module.exports = { extends: ['@commitlint/config-conventional'],
    rules: {
        'type-enum': [
            2,
            'always',
            [
                'feat',    // New feature: introducing new functionality
                'fix',     // Bugfix: fixing a bug
                'docs',    // Docs: documentation only changes
                'style',   // Style mod: formatting, white-space, etc
                'refactor',// Refactor: A code change that neither fixes a bug nor adds a feature
                'test',    // Test: adding missing tests
                'chore',   // Chore: changes that don't modify src or test files
                'patch'    // Patch: small changes
            ]
        ]
    }
};
