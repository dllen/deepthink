# Developer Guide

## Database Content Security

This project uses an encrypted SQLite database to store web content. To work with the database locally or deploy updates, you need to configure the encryption key.

### Local Development Setup

1.  **Set the Environment Variable**:
    You need to set the `SQLITE_KEY` environment variable in your terminal. This key is used to encrypt and decrypt the `python_scripts/web_content.db` file.

    ```bash
    export SQLITE_KEY="your_secret_password_here"
    ```

    *Tip: Add this line to your shell profile (`.zshrc` or `.bashrc`) to make it permanent.*

2.  **Encrypting the Database**:
    Before committing changes to the database, run the helper script to encrypt it:

    ```bash
    ./scripts/encrypt-db.sh
    ```

    This will create `python_scripts/web_content.db.enc`.
    **Note**: The raw `web_content.db` is ignored by git to prevent accidental leaks.

### GitHub Actions Configuration

To ensure the deployment workflow can decrypt the database:

1.  Go to your GitHub Repository.
2.  Navigate to **Settings** > **Secrets and variables** > **Actions**.
3.  Click **New repository secret**.
4.  **Name**: `SQLITE_KEY`
5.  **Value**: Enter the same secret key you used locally.
6.  Click **Add secret**.

The `deploy.yml` workflow is configured to automatically use this secret to decrypt the database during the build process.
