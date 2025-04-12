import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { Pool } from 'pg';
import { config } from 'dotenv';

// Load environment variables
config();

interface Migration {
  id: number;
  name: string;
  filename: string;
  appliedAt: Date | null;
  hash: string;
}

class MigrationManager {
  private pool: Pool;
  private migrationsDir: string;
  private backupDir: string;

  constructor() {
    this.pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    this.migrationsDir = path.join(process.cwd(), 'migrations');
    this.backupDir = path.join(process.cwd(), 'migrations', 'backup');
  }

  private async ensureMigrationTable(): Promise<void> {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        filename VARCHAR(255) NOT NULL,
        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        hash VARCHAR(64) NOT NULL
      );
    `);
  }

  private async getCurrentMigrations(): Promise<Migration[]> {
    const result = await this.pool.query('SELECT * FROM migrations ORDER BY id ASC');
    return result.rows.map(row => ({
      id: row.id,
      name: row.name,
      filename: row.filename,
      appliedAt: row.applied_at,
      hash: row.hash
    }));
  }

  private calculateHash(content: string): string {
    const crypto = require('crypto');
    return crypto.createHash('sha256').update(content).digest('hex');
  }

  public async consolidateMigrations(): Promise<void> {
    console.log('Starting migration consolidation...');

    // Create backup directory if it doesn't exist
    if (!fs.existsSync(this.backupDir)) {
      fs.mkdirSync(this.backupDir, { recursive: true });
    }

    // Get all migration files
    const files = fs.readdirSync(this.migrationsDir)
      .filter(f => f.endsWith('.sql'))
      .sort();

    // Backup existing migrations
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = path.join(this.backupDir, `backup_${timestamp}`);
    fs.mkdirSync(backupPath);

    files.forEach(file => {
      fs.copyFileSync(
        path.join(this.migrationsDir, file),
        path.join(backupPath, file)
      );
    });

    // Get current database schema
    const schemaPath = path.join(this.migrationsDir, 'consolidated_schema.sql');
    execSync(`pg_dump --schema-only --no-owner --no-acl -d ${process.env.DATABASE_URL} > ${schemaPath}`);

    // Clear old migration files
    files.forEach(file => {
      const filePath = path.join(this.migrationsDir, file);
      if (file !== 'consolidated_schema.sql') {
        fs.unlinkSync(filePath);
      }
    });

    // Update migrations table
    await this.pool.query('TRUNCATE migrations');
    await this.pool.query(`
      INSERT INTO migrations (name, filename, hash)
      VALUES ($1, $2, $3)
    `, [
      'consolidated_schema',
      'consolidated_schema.sql',
      this.calculateHash(fs.readFileSync(schemaPath, 'utf8'))
    ]);

    console.log('Migration consolidation completed successfully.');
  }

  public async createRollbackProcedure(): Promise<void> {
    console.log('Creating rollback procedures...');

    const rollbackPath = path.join(this.migrationsDir, 'rollback');
    if (!fs.existsSync(rollbackPath)) {
      fs.mkdirSync(rollbackPath, { recursive: true });
    }

    // Create rollback script
    const rollbackScript = `
    -- Rollback to specific point function
    CREATE OR REPLACE FUNCTION rollback_to_version(target_version INTEGER) RETURNS void AS $$
    DECLARE
      current_version INTEGER;
    BEGIN
      -- Get current version
      SELECT MAX(id) INTO current_version FROM migrations;
      
      IF target_version >= current_version THEN
        RAISE EXCEPTION 'Target version must be less than current version';
      END IF;
      
      -- Create savepoint
      EXECUTE 'SAVEPOINT rollback_point';
      
      BEGIN
        -- Execute rollback logic
        EXECUTE format('SELECT rollback_version_%s()', target_version);
        
        -- Update migrations table
        DELETE FROM migrations WHERE id > target_version;
        
        COMMIT;
      EXCEPTION WHEN OTHERS THEN
        -- Rollback to savepoint if anything fails
        EXECUTE 'ROLLBACK TO SAVEPOINT rollback_point';
        RAISE EXCEPTION 'Rollback failed: %', SQLERRM;
      END;
    END;
    $$ LANGUAGE plpgsql;

    -- Function to backup data before rollback
    CREATE OR REPLACE FUNCTION backup_before_rollback() RETURNS void AS $$
    BEGIN
      -- Create backup schema
      CREATE SCHEMA IF NOT EXISTS backup_schema;
      
      -- Copy tables to backup schema
      FOR table_name IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public')
      LOOP
        EXECUTE format('CREATE TABLE backup_schema.%I AS SELECT * FROM public.%I', table_name, table_name);
      END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    -- Function to verify database integrity
    CREATE OR REPLACE FUNCTION verify_db_integrity() RETURNS boolean AS $$
    DECLARE
      error_count INTEGER;
    BEGIN
      -- Check for orphaned records
      SELECT COUNT(*) INTO error_count
      FROM (
        -- Add specific integrity checks here
        -- Example: Check for orphaned user data
        SELECT id FROM users u
        LEFT JOIN user_profiles up ON u.id = up.user_id
        WHERE up.user_id IS NULL
      ) as errors;
      
      RETURN error_count = 0;
    END;
    $$ LANGUAGE plpgsql;
    `;

    fs.writeFileSync(
      path.join(rollbackPath, 'rollback_procedures.sql'),
      rollbackScript
    );

    // Create index verification script
    const indexVerificationScript = `
    -- Function to verify indexes
    CREATE OR REPLACE FUNCTION verify_indexes() RETURNS TABLE (
      table_name text,
      index_name text,
      is_valid boolean,
      missing_indexes text[]
    ) AS $$
    BEGIN
      RETURN QUERY
      WITH recommended_indexes AS (
        -- Add your recommended indexes here
        SELECT 'users' as table_name, 
               ARRAY['email_idx', 'created_at_idx'] as required_indexes
        UNION ALL
        SELECT 'form_analysis',
               ARRAY['user_id_idx', 'created_at_idx']
        -- Add more tables and their required indexes
      )
      SELECT 
        ri.table_name::text,
        i.indexname::text,
        (NOT EXISTS (
          SELECT 1 FROM pg_stat_user_indexes ui 
          WHERE ui.schemaname = 'public' 
          AND ui.indexrelname = i.indexname 
          AND NOT ui.idx_isvalid
        )) as is_valid,
        ARRAY(
          SELECT idx 
          FROM unnest(ri.required_indexes) idx 
          WHERE NOT EXISTS (
            SELECT 1 FROM pg_indexes pi 
            WHERE pi.schemaname = 'public' 
            AND pi.tablename = ri.table_name 
            AND pi.indexname = idx
          )
        ) as missing_indexes
      FROM recommended_indexes ri
      LEFT JOIN pg_indexes i ON i.tablename = ri.table_name
      WHERE i.schemaname = 'public';
    END;
    $$ LANGUAGE plpgsql;
    `;

    fs.writeFileSync(
      path.join(rollbackPath, 'verify_indexes.sql'),
      indexVerificationScript
    );

    console.log('Rollback procedures created successfully.');
  }

  public async verifyIndexes(): Promise<void> {
    console.log('Verifying database indexes...');

    const result = await this.pool.query('SELECT * FROM verify_indexes()');
    
    result.rows.forEach(row => {
      console.log(`\nTable: ${row.table_name}`);
      console.log(`Index: ${row.index_name || 'No index'}`);
      console.log(`Valid: ${row.is_valid}`);
      if (row.missing_indexes.length > 0) {
        console.log('Missing indexes:', row.missing_indexes);
      }
    });
  }

  public async cleanup(): Promise<void> {
    await this.pool.end();
  }
}

// CLI interface
async function main() {
  const manager = new MigrationManager();

  try {
    const command = process.argv[2];
    
    switch (command) {
      case 'consolidate':
        await manager.consolidateMigrations();
        break;
      case 'create-rollback':
        await manager.createRollbackProcedure();
        break;
      case 'verify-indexes':
        await manager.verifyIndexes();
        break;
      default:
        console.log('Available commands: consolidate, create-rollback, verify-indexes');
    }
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  } finally {
    await manager.cleanup();
  }
}

if (require.main === module) {
  main();
}

export default MigrationManager; 