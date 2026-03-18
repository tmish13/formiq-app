const path = require('path');
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

    // @tensorflow-models/pose-detection statically references tfjs-backend-webgpu
    // in its dist bundle even though we only use tfjs-backend-webgl.
    // Stub it out so webpack doesn't fail trying to resolve the WebGPU package.
    config.resolve.alias = {
      ...config.resolve.alias,
      '@tensorflow/tfjs-backend-webgpu': path.resolve(
        __dirname,
        'src/utils/webgpu-stub.js'
      ),
    };

    return config;
  }
);