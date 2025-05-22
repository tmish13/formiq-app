import * as fs from 'fs';
import * as path from 'path';
import { Project } from 'ts-morph';

// Use correct paths
const FRONTEND_ROOT = path.resolve(process.cwd(), '../frontend');
const SRC_PATH = path.join(FRONTEND_ROOT, 'src');

console.log('Starting frontend codebase inventory...');
console.log('Frontend root:', FRONTEND_ROOT);
console.log('Source path:', SRC_PATH);

try {
  // Initialize a new ts-morph project
  const project = new Project();

  // Add TypeScript configuration if available
  const tsConfigPath = path.join(FRONTEND_ROOT, 'tsconfig.json');
  if (fs.existsSync(tsConfigPath)) {
    console.log('Using TypeScript config:', tsConfigPath);
    project.addSourceFilesFromTsConfig(tsConfigPath);
  } else {
    console.log('No tsconfig.json found, adding source files directly');
    // Add all TypeScript and TSX files in the frontend/src directory
    project.addSourceFilesAtPaths([path.join(SRC_PATH, '**/*.{ts,tsx}')]);
  }

  const sourceFiles = project.getSourceFiles();
  console.log(`Found ${sourceFiles.length} source files to process`);

  // Create a new inventory
  const inventory = {
    components: new Map(),
    hooks: new Map(),
    slices: new Map(),
    services: new Map(),
    contexts: new Map(),
    importGraph: new Map(),
    exportedSymbols: new Map(),
  };

  // Process each source file
  sourceFiles.forEach((sourceFile, index) => {
    try {
      if (index % 50 === 0) {
        console.log(`Processing file ${index + 1}/${sourceFiles.length}...`);
      }
      
      const filePath = sourceFile.getFilePath();
      const relativePath = path.relative(FRONTEND_ROOT, filePath);
      
      // Skip test files and mocks
      if (filePath.includes('__tests__') || 
          filePath.includes('.test.') || 
          filePath.includes('.spec.') || 
          filePath.includes('__mocks__')) {
        return;
      }

      const fileInfo = {
        path: relativePath,
        components: [],
        hooks: [],
        slices: [],
        services: [],
        contexts: [],
        imports: [],
        exports: [],
      };

      // Process imports
      processImports(sourceFile, fileInfo, inventory);
      
      // Process exports
      processExports(sourceFile, fileInfo, inventory);
      
      // Process React components
      processComponents(sourceFile, fileInfo);
      
      // Process custom hooks
      processHooks(sourceFile, fileInfo);
      
      // Process Redux slices
      processSlices(sourceFile, fileInfo);
      
      // Process services
      processServices(sourceFile, fileInfo);
      
      // Process contexts
      processContexts(sourceFile, fileInfo);
      
      // Update the inventory
      updateInventory(fileInfo, inventory);
    } catch (error) {
      console.error(`Error processing file: ${sourceFile.getFilePath()}`, error);
    }
  });

  // Generate the unused files report
  const unusedFiles = detectUnusedFiles(project, inventory);
  fs.writeFileSync('/tmp/unused-frontend.txt', unusedFiles.join('\n'));
  console.log(`Found ${unusedFiles.length} potentially unused files`);

  // Save inventory results
  fs.writeFileSync('/tmp/frontend-inventory.json', JSON.stringify({
    components: Object.fromEntries(inventory.components),
    hooks: Object.fromEntries(inventory.hooks),
    slices: Object.fromEntries(inventory.slices),
    services: Object.fromEntries(inventory.services),
    contexts: Object.fromEntries(inventory.contexts),
    exportedSymbols: Object.fromEntries(inventory.exportedSymbols),
  }, null, 2));

  // Save import graph
  fs.writeFileSync('/tmp/import-graph.json', JSON.stringify({
    importGraph: [...inventory.importGraph.entries()].reduce((acc, [key, value]) => {
      acc[key] = [...value];
      return acc;
    }, {}),
  }, null, 2));

  console.log('🎉 Inventory complete!');
  console.log('📊 Results saved to:');
  console.log('   - /tmp/frontend-inventory.json');
  console.log('   - /tmp/import-graph.json');
  console.log('   - /tmp/unused-frontend.txt');
} catch (error) {
  console.error('Fatal error:', error);
  process.exit(1);
}

// Helper Functions

function processImports(sourceFile, fileInfo, inventory) {
  try {
    const importDeclarations = sourceFile.getImportDeclarations();
    
    importDeclarations.forEach((importDecl) => {
      const moduleSpecifier = importDecl.getModuleSpecifierValue();
      
      // Skip node_modules imports
      if (!moduleSpecifier.startsWith('.') && !moduleSpecifier.startsWith('/')) {
        return;
      }
      
      const namedImports = [];
      let defaultImport = null;
      
      try {
        defaultImport = importDecl.getDefaultImport()?.getText() || null;
      } catch (error) {
        // Ignore default import errors
      }
      
      try {
        importDecl.getNamedImports().forEach((namedImport) => {
          namedImports.push(namedImport.getName());
        });
      } catch (error) {
        // Ignore named import errors
      }
      
      fileInfo.imports.push({
        path: moduleSpecifier,
        names: namedImports,
        isDefaultImport: !!defaultImport,
      });
      
      // Add to import graph
      if (!inventory.importGraph.has(fileInfo.path)) {
        inventory.importGraph.set(fileInfo.path, new Set());
      }
      
      // Resolve relative paths to absolute
      const importedFilePath = resolveImportPath(sourceFile.getFilePath(), moduleSpecifier);
      if (importedFilePath) {
        const relativeImportedPath = path.relative(FRONTEND_ROOT, importedFilePath);
        inventory.importGraph.get(fileInfo.path).add(relativeImportedPath);
      }
    });
  } catch (error) {
    console.error(`Error processing imports for ${sourceFile.getFilePath()}:`, error);
  }
}

function processExports(sourceFile, fileInfo, inventory) {
  try {
    // Get all export declarations
    const exportDeclarations = sourceFile.getExportDeclarations();
    const exportAssignments = sourceFile.getExportAssignments();
    const exportedSymbols = [];
    
    // Process named exports
    exportDeclarations.forEach((exportDecl) => {
      try {
        exportDecl.getNamedExports().forEach((namedExport) => {
          exportedSymbols.push(namedExport.getName());
          fileInfo.exports.push(namedExport.getName());
        });
      } catch (error) {
        // Ignore errors for individual named exports
      }
    });
    
    // Process default exports
    exportAssignments.forEach((exportAssignment) => {
      try {
        if (exportAssignment.isExportEquals()) return;
        
        const expression = exportAssignment.getExpression();
        const expressionText = expression.getText();
        
        if (Node.isIdentifier(expression)) {
          exportedSymbols.push(expressionText);
          fileInfo.exports.push(expressionText);
        } else if (expressionText.includes('function') || expressionText.includes('=>')) {
          // It's an anonymous function export
          exportedSymbols.push('default');
          fileInfo.exports.push('default');
        } else if (expressionText.includes('React.') || expressionText.includes('styled')) {
          // It's likely a component
          exportedSymbols.push('default');
          fileInfo.exports.push('default');
        }
      } catch (error) {
        // Ignore errors for individual exports
      }
    });
    
    // Also check exported variables, functions, interfaces, etc.
    try {
      sourceFile.getVariableDeclarations().forEach((varDecl) => {
        try {
          if (varDecl.isExported()) {
            exportedSymbols.push(varDecl.getName());
            fileInfo.exports.push(varDecl.getName());
          }
        } catch (error) {
          // Ignore errors for individual variables
        }
      });
    } catch (error) {
      // Ignore variable declaration errors
    }
    
    try {
      sourceFile.getFunctions().forEach((func) => {
        try {
          if (func.isExported()) {
            exportedSymbols.push(func.getName() || 'anonymous');
            fileInfo.exports.push(func.getName() || 'anonymous');
          }
        } catch (error) {
          // Ignore errors for individual functions
        }
      });
    } catch (error) {
      // Ignore function errors
    }
    
    try {
      sourceFile.getClasses().forEach((classDecl) => {
        try {
          if (classDecl.isExported()) {
            exportedSymbols.push(classDecl.getName());
            fileInfo.exports.push(classDecl.getName());
          }
        } catch (error) {
          // Ignore errors for individual classes
        }
      });
    } catch (error) {
      // Ignore class errors
    }
    
    try {
      sourceFile.getInterfaces().forEach((interfaceDecl) => {
        try {
          if (interfaceDecl.isExported()) {
            exportedSymbols.push(interfaceDecl.getName());
            fileInfo.exports.push(interfaceDecl.getName());
          }
        } catch (error) {
          // Ignore errors for individual interfaces
        }
      });
    } catch (error) {
      // Ignore interface errors
    }
    
    inventory.exportedSymbols.set(fileInfo.path, exportedSymbols);
  } catch (error) {
    console.error(`Error processing exports for ${sourceFile.getFilePath()}:`, error);
  }
}

function processComponents(sourceFile, fileInfo) {
  try {
    const filePath = sourceFile.getFilePath();
    const SyntaxKind = { ArrowFunction: 'ArrowFunction' };
    const Node = { isIdentifier: (node) => node.getKind() === 'Identifier' };
    
    // 1. Files ending with .tsx are likely components
    if (filePath.endsWith('.tsx') && !filePath.includes('test')) {
      // Check for function declarations or arrow functions that might be components
      try {
        const functionDeclarations = sourceFile.getFunctions();
        
        // Look for functions that return JSX elements
        functionDeclarations.forEach((func) => {
          try {
            const functionName = func.getName();
            if (!functionName) return;
            
            // Check if the function name starts with an uppercase letter (React component convention)
            if (/^[A-Z]/.test(functionName)) {
              fileInfo.components.push(functionName);
            }
          } catch (error) {
            // Ignore individual function errors
          }
        });
      } catch (error) {
        // Ignore function declaration errors
      }
      
      try {
        const variableDeclarations = sourceFile.getVariableDeclarations();
        
        // Look for arrow functions or variables that might be components
        variableDeclarations.forEach((varDecl) => {
          try {
            const variableName = varDecl.getName();
            if (!variableName) return;
            
            // Check if the variable name starts with an uppercase letter (React component convention)
            if (/^[A-Z]/.test(variableName)) {
              const initializer = varDecl.getInitializer();
              if (initializer) {
                const initializerText = initializer.getText();
                if (
                  initializer.getKind() === SyntaxKind.ArrowFunction ||
                  initializerText.includes('React.') ||
                  initializerText.includes('styled') ||
                  initializerText.includes('memo') ||
                  initializerText.includes('JSX')
                ) {
                  fileInfo.components.push(variableName);
                }
              }
            }
          } catch (error) {
            // Ignore individual variable errors
          }
        });
      } catch (error) {
        // Ignore variable declaration errors
      }
    }
  } catch (error) {
    console.error(`Error processing components for ${sourceFile.getFilePath()}:`, error);
  }
}

function processHooks(sourceFile, fileInfo) {
  try {
    const filePath = sourceFile.getFilePath();
    const SyntaxKind = { ArrowFunction: 'ArrowFunction' };
    
    // Files with "hooks" in the path or functions starting with "use"
    if (filePath.includes('/hooks/') || filePath.includes('Hook') || filePath.includes('hook')) {
      // Find all exported functions that start with "use"
      try {
        const functionDeclarations = sourceFile.getFunctions();
        
        functionDeclarations.forEach((func) => {
          try {
            const functionName = func.getName();
            if (functionName && functionName.startsWith('use')) {
              fileInfo.hooks.push(functionName);
            }
          } catch (error) {
            // Ignore individual function errors
          }
        });
      } catch (error) {
        // Ignore function declaration errors
      }
      
      try {
        const variableDeclarations = sourceFile.getVariableDeclarations();
        
        variableDeclarations.forEach((varDecl) => {
          try {
            const variableName = varDecl.getName();
            if (variableName && variableName.startsWith('use')) {
              const initializer = varDecl.getInitializer();
              if (initializer) {
                const initializerText = initializer.getText();
                if (
                  initializer.getKind() === SyntaxKind.ArrowFunction ||
                  initializerText.includes('function')
                ) {
                  fileInfo.hooks.push(variableName);
                }
              }
            }
          } catch (error) {
            // Ignore individual variable errors
          }
        });
      } catch (error) {
        // Ignore variable declaration errors
      }
    }
  } catch (error) {
    console.error(`Error processing hooks for ${sourceFile.getFilePath()}:`, error);
  }
}

function processSlices(sourceFile, fileInfo) {
  try {
    const filePath = sourceFile.getFilePath();
    const Node = {
      isCallExpression: (node) => node.getKind() === 'CallExpression',
      isObjectLiteralExpression: (node) => node.getKind() === 'ObjectLiteralExpression',
      isPropertyAssignment: (node) => node.getKind() === 'PropertyAssignment',
      isStringLiteral: (node) => node.getKind() === 'StringLiteral'
    };
    
    // Files in the store directory or with "slice" in the name
    if (filePath.includes('/store/') || filePath.includes('slice') || filePath.includes('reducer')) {
      // Look for createSlice calls
      try {
        sourceFile.forEachDescendant((node) => {
          try {
            if (Node.isCallExpression(node)) {
              const expression = node.getExpression();
              if (expression.getText() === 'createSlice') {
                
                // Get the object literal argument
                const args = node.getArguments();
                if (args.length > 0 && Node.isObjectLiteralExpression(args[0])) {
                  const objLiteral = args[0];
                  
                  // Find the name property
                  for (const prop of objLiteral.getProperties()) {
                    if (Node.isPropertyAssignment(prop) && 
                        prop.getName() === 'name') {
                      
                      const initializer = prop.getInitializer();
                      if (Node.isStringLiteral(initializer)) {
                        // Get the slice name
                        const sliceName = initializer.getText().replace(/['"]/g, '');
                        fileInfo.slices.push(sliceName);
                      }
                    }
                  }
                }
              }
            }
          } catch (error) {
            // Ignore errors for individual nodes
          }
        });
      } catch (error) {
        // Ignore descendant errors
      }
      
      // Also check for reducer creators
      try {
        sourceFile.getVariableDeclarations().forEach((varDecl) => {
          try {
            const varName = varDecl.getName();
            if (varName && (varName.includes('Reducer') || varName.includes('Slice'))) {
              fileInfo.slices.push(varName);
            }
          } catch (error) {
            // Ignore individual variable errors
          }
        });
      } catch (error) {
        // Ignore variable declaration errors
      }
    }
  } catch (error) {
    console.error(`Error processing slices for ${sourceFile.getFilePath()}:`, error);
  }
}

function processServices(sourceFile, fileInfo) {
  try {
    const filePath = sourceFile.getFilePath();
    
    // Files in the services directory or with "service" or "api" in the name
    if (filePath.includes('/services/') || 
        filePath.includes('service') || 
        filePath.includes('api') || 
        filePath.includes('client')) {
      
      // Look for exported objects or functions that might be services
      try {
        sourceFile.getExportedDeclarations().forEach((declarations, name) => {
          if (name !== 'default') {
            fileInfo.services.push(name);
          }
        });
      } catch (error) {
        // Ignore export declaration errors
      }
      
      // Check default exports too
      try {
        const defaultExport = sourceFile.getDefaultExportSymbol();
        if (defaultExport) {
          fileInfo.services.push(defaultExport.getName());
        }
      } catch (error) {
        // Ignore default export errors
      }
    }
  } catch (error) {
    console.error(`Error processing services for ${sourceFile.getFilePath()}:`, error);
  }
}

function processContexts(sourceFile, fileInfo) {
  try {
    const filePath = sourceFile.getFilePath();
    const Node = {
      isCallExpression: (node) => node.getKind() === 'CallExpression',
      isVariableDeclaration: (node) => node.getKind() === 'VariableDeclaration'
    };
    
    // Files in the contexts directory or with "context" in the name
    if (filePath.includes('/contexts/') || filePath.includes('context') || filePath.includes('Context')) {
      
      // Look for createContext calls
      try {
        sourceFile.forEachDescendant((node) => {
          try {
            if (Node.isCallExpression(node)) {
              const expression = node.getExpression();
              if (expression.getText().includes('createContext')) {
                
                // Try to find the variable that holds this context
                const parent = node.getParent();
                if (Node.isVariableDeclaration(parent)) {
                  const contextName = parent.getName();
                  fileInfo.contexts.push(contextName);
                }
              }
            }
          } catch (error) {
            // Ignore errors for individual nodes
          }
        });
      } catch (error) {
        // Ignore descendant errors
      }
      
      // Also look for exported variables with Context in the name
      try {
        sourceFile.getVariableDeclarations().forEach((varDecl) => {
          try {
            const varName = varDecl.getName();
            if (varName && varName.includes('Context')) {
              fileInfo.contexts.push(varName);
            }
          } catch (error) {
            // Ignore individual variable errors
          }
        });
      } catch (error) {
        // Ignore variable declaration errors
      }
    }
  } catch (error) {
    console.error(`Error processing contexts for ${sourceFile.getFilePath()}:`, error);
  }
}

function updateInventory(fileInfo, inventory) {
  // Add components to inventory
  if (fileInfo.components.length > 0) {
    inventory.components.set(fileInfo.path, fileInfo.components);
  }
  
  // Add hooks to inventory
  if (fileInfo.hooks.length > 0) {
    inventory.hooks.set(fileInfo.path, fileInfo.hooks);
  }
  
  // Add slices to inventory
  if (fileInfo.slices.length > 0) {
    inventory.slices.set(fileInfo.path, fileInfo.slices);
  }
  
  // Add services to inventory
  if (fileInfo.services.length > 0) {
    inventory.services.set(fileInfo.path, fileInfo.services);
  }
  
  // Add contexts to inventory
  if (fileInfo.contexts.length > 0) {
    inventory.contexts.set(fileInfo.path, fileInfo.contexts);
  }
}

function resolveImportPath(currentFilePath, importPath) {
  try {
    const currentDir = path.dirname(currentFilePath);
    
    // Handle relative imports
    if (importPath.startsWith('.')) {
      let resolvedPath = path.resolve(currentDir, importPath);
      
      // Try to find the actual file by adding extensions if needed
      if (!fs.existsSync(resolvedPath)) {
        for (const ext of ['.ts', '.tsx', '.js', '.jsx']) {
          if (fs.existsSync(`${resolvedPath}${ext}`)) {
            return `${resolvedPath}${ext}`;
          }
          
          // Check for index files
          if (fs.existsSync(path.join(resolvedPath, `index${ext}`))) {
            return path.join(resolvedPath, `index${ext}`);
          }
        }
        return null;
      }
      
      return resolvedPath;
    }
    
    // Handle absolute imports within the project
    if (importPath.startsWith('/')) {
      const projectRoot = FRONTEND_ROOT;
      return path.join(projectRoot, importPath);
    }
    
    return null;
  } catch (error) {
    console.error(`Error resolving import path: ${importPath} from ${currentFilePath}`, error);
    return null;
  }
}

function detectUnusedFiles(project, inventory) {
  try {
    const unusedFiles = [];
    const allFiles = project.getSourceFiles().map(file => 
      path.relative(FRONTEND_ROOT, file.getFilePath())
    );
    
    // Create a set of all imported files
    const importedFiles = new Set();
    inventory.importGraph.forEach((imported) => {
      imported.forEach(file => importedFiles.add(file));
    });
    
    // Check each file to see if it's imported anywhere
    allFiles.forEach(file => {
      // Skip test files and type definitions
      if (file.includes('__tests__') || 
          file.includes('.test.') || 
          file.includes('.spec.') || 
          file.includes('__mocks__') ||
          file.includes('.d.ts')) {
        return;
      }
      
      // Skip entry point files like index.ts, App.tsx
      if (file.includes('index.ts') || 
          file.includes('index.tsx') || 
          file.includes('App.tsx')) {
        return;
      }
      
      // Skip files in node_modules
      if (file.includes('node_modules')) {
        return;
      }
      
      // If this file is not imported anywhere, flag it as unused
      if (!importedFiles.has(file)) {
        unusedFiles.push(file);
      }
    });
    
    return unusedFiles;
  } catch (error) {
    console.error('Error detecting unused files:', error);
    return [];
  }
} 