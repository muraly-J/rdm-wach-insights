// Replaces import.meta.env with {} for Jest (Vite-specific, not available in Node)
const importMetaEnvPlugin = () => ({
  visitor: {
    MemberExpression(path) {
      if (
        path.node.object.type === 'MetaProperty' &&
        path.node.object.meta.name === 'import' &&
        path.node.object.property.name === 'meta' &&
        path.node.property.name === 'env'
      ) {
        path.replaceWithSourceString('{}');
      }
    },
  },
});

module.exports = {
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' } }],
    ['@babel/preset-react', { runtime: 'automatic' }],
    '@babel/preset-typescript',
  ],
  plugins: [importMetaEnvPlugin],
};
