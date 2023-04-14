var path = require("path");
var webpack = require('webpack');
var BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");


var fs = require("fs");

function getReactChunks(){
  // Add all jsx files in /assets/js as entries
  var files = fs.readdirSync('./frontend/').filter(function(f){
    return f.endsWith('.jsx');
  })

  var entries = {};
  files.forEach(function(f){
    entries[f.replace(/.jsx/, '')] = ['babel-polyfill', './frontend/' + f];
  });
  return entries;
}

const reactBuild = {
  name: 'react',
  context: __dirname,
  entry: getReactChunks(),
  output: {
    path: path.resolve('./assets/dist/'),
    filename: "[name]-[hash].js",
    //clean: true, //TODO - merge style and react builds before adding clean
  },
  devtool: 'source-map',
  module: {
    rules: [
      {
        test: /\.scss$/,
        use: [
          { loader: 'style-loader'},
          { loader: 'css-loader'},
          { loader: 'sass-loader'}
        ]
      },
      {
        test: /\.css$/,
        use: [
          { loader: 'style-loader'},
          { loader: 'css-loader'}
        ]
      },
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        loader: 'babel-loader'
      },
    ],
  },
  externals: {
    jquery: 'jQuery',
    $: 'jQuery'
  },
  optimization: {
    //runtimeChunk: "single", // enable "runtime" chunk
    splitChunks: {
      cacheGroups: {
        common: {
          name: 'common',
          chunks: 'initial',
          minChunks: 3
        }
      }
    }
  },
  plugins: [
    new webpack.IgnorePlugin(
      { resourceRegExp: /^\.\/locale$/ }),//TODO, /moment$/),
    new BundleTracker({filename: './assets/frontend-webpack-manifest.json'}),
  ],
  resolve: {
    modules: [
      path.join(__dirname, "assets/js"),
      path.join(__dirname, "frontend"),
      'node_modules',
    ],
    extensions: ['.js', '.jsx', '.scss']
  },
};

const styleBuild = {
  name: 'css',
  entry: {
    'p2pu-strap': './static/sass/p2pu-custom.scss'
  },
  module: {
    rules: [
      {
        test: /\.woff2?$|\.ttf$|\.eot$|\.svg$|\.png$/,
        type: 'asset/resource',
      },
      {
        test: /\.scss$/,
        use: [
          { loader: MiniCssExtractPlugin.loader },
          {
            loader: 'css-loader',
            options: {
              sourceMap: true,
            },
          },
          { loader: 'resolve-url-loader' },
          {
            loader: 'sass-loader',
            options: {
              sourceMap: true,
              //includePaths: [path.resolve("./static/"), path.resolve("./node_modules/")]
            }
          }
        ]
      },
    ]
  },
  output: {
    path: path.resolve('./assets/dist/'),
    filename: "[name].[hash].js",
    assetModuleFilename: '[name]-[hash][ext][query]',
  },
  plugins: [
    new MiniCssExtractPlugin({filename: "[name].[hash].css"}),
    new BundleTracker({filename: './assets/style-webpack-manifest.json'}),
  ],
}

module.exports = [reactBuild, styleBuild]
