const path = require('path');

module.exports = {
	entry: './src/index.tsx',
	output: {
		path: path.resolve(__dirname, '../static/js'),
		filename: 'voice-interface.js',
		library: 'VoiceInterface',
		libraryTarget: 'umd',
		globalObject: 'this'
	},
	resolve: {
		extensions: ['.tsx', '.ts', '.js', '.jsx']
	},
	module: {
		rules: [
			{
				test: /\.(ts|tsx)$/,
				exclude: /node_modules/,
				use: {
					loader: 'babel-loader',
					options: {
						presets: [
							'@babel/preset-env',
							'@babel/preset-react',
							'@babel/preset-typescript'
						]
					}
				}
			},
			{
				test: /\.(js|jsx)$/,
				exclude: /node_modules/,
				use: {
					loader: 'babel-loader',
					options: {
						presets: [
							'@babel/preset-env',
							'@babel/preset-react'
						]
					}
				}
			}
		]
	},
	externals: {
		'react': 'React',
		'react-dom': 'ReactDOM'
	},
	devtool: 'source-map'
};