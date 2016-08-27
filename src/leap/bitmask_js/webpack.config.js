var path = require('path')
var webpack = require('webpack')
var CopyWebpackPlugin = require('copy-webpack-plugin');

var config = {
  context: path.join(__dirname, 'app'),
  entry: './main.js',
  output: {
    path: path.join(__dirname, 'public'),
    filename: 'app.bundle.js'
  },
  resolve: {
    modulesDirectories: ['node_modules', './app'],
    extensions: ['', '.js', '.jsx']
  },
  module: {
    loaders: [
      // babel transform
      {
        test: /\.js$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
        query: {
          presets: ['react', 'es2015']
        }
      },
      {
        test: /\.css$/,
        loader: "style!css"
      },
      {
        test: /\.less$/,
        loader: "style!css!less?noIeCompat"
      }
    ]
  },
  plugins: [
    // don't bundle when there is an error:
    new webpack.NoErrorsPlugin(),

    // https://webpack.github.io/docs/code-splitting.html
    // new webpack.optimize.CommonChunkPlugin('common.js')

    // https://github.com/kevlened/copy-webpack-plugin
    new CopyWebpackPlugin([
      { from: 'css/*.css' },
      { from: 'img/*'},
      { from: 'index.html' },
      { from: '../node_modules/bootstrap/dist/css/bootstrap.min.css', to: 'css' },
      { from: '../node_modules/bootstrap/dist/fonts/glyphicons-halflings-regular.woff2', to: 'fonts' },
      { from: '../node_modules/zxcvbn/dist/zxcvbn.js', to: 'js' }
    ])
  ],
  stats: {
    colors: true
  },
  // source-map can be used in production or development
  // but it creates a separate file.
  devtool: 'source-map'
}

/*
if (process.env.NODE_ENV == 'production') {
  // see https://github.com/webpack/docs/wiki/optimization
  config.plugins.push(
    new webpack.optimize.UglifyJsPlugin({
      compress: { warnings: false },
      output: { comments: false }
    }),
    new webpack.optimize.DedupePlugin()
  )
} else {
  config.devtool = 'inline-source-map';
}
*/

module.exports = config
