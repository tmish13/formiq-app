const { override, disableEsLint, addBabelPlugin } = require('customize-cra');

module.exports = override(
  // Disable ESLint during development
  disableEsLint(),
  
  // Add babel plugins to handle TypeScript issues
  addBabelPlugin([
    '@babel/plugin-transform-typescript',
    { allowDeclareFields: true }
  ]),
  
  // Custom webpack config
  (config) => {
    // Disable type checking
    const plugins = config.plugins.filter(plugin => 
      plugin.constructor.name !== 'ForkTsCheckerWebpackPlugin'
    );
    config.plugins = plugins;
    
    // Disable Fast Refresh
    config.plugins = config.plugins.filter(plugin =>
      plugin.constructor.name !== 'ReactRefreshPlugin'
    );
    
    return config;
  }
);