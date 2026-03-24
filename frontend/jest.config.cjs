/** @type {import('jest').Config} */

// Inline Babel plugin that replaces `import.meta.env` with a plain object.
// Required because import.meta.env is Vite-specific and not available in Jest/Node.
const importMetaEnvPlugin = () => ({
  visitor: {
    MemberExpression(path) {
      if (
        path.node.object.type === 'MetaProperty' &&
        path.node.object.meta.name === 'import' &&
        path.node.object.property.name === 'meta' &&
        path.node.property.name === 'env'
      ) {
        // Replace import.meta.env with an empty object literal
        path.replaceWithSourceString('{}');
      }
    },
  },
});

const config = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { plugins: [importMetaEnvPlugin] }],
  },
  moduleNameMapper: {
    '\\.(css|less)$': '<rootDir>/src/__mocks__/styleMock.js',
  },
  testMatch: ['**/__tests__/**/*.[jt]s?(x)', '**/?(*.)+(spec|test).[jt]s?(x)'],
};

module.exports = config;
