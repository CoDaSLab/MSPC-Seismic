## SSH connection tutorial

This is a guide for establishing a connection via SSH key from your server to a remote server for downloading data files and other purposes.

### 1. Open Git Bash

### 2. Run `cd ~/.ssh`
This will change your current directory to the one where SSH keys are stored.

### 3. Run `ssh-keygen -t rsa`

This will create a new SSH key.

### 4. Enter a name of your new key.

If you leave it blank, it will default to *id_rsa*.

### 5. Enter a passphrase for your new key.

You can leave it blank if you don't want a passphrase. You will also be asked to confirm your passphrase.

Your SSH key is now created. If your run `ls`, you should see two files with the name you entered in Step 4, one without an extension and the other with a .pub extension. These are your private and public keys, respectively.

Steps 6-8 explain how to assign your new private key to an SSH agent so you don't need to enter the passphrase every time you use the key. This is optional, and only useful if you entered a passphrase for your SSH key in Step 5.

### 6. *(Optional)* Run ``eval `ssh agent` ``.

### 7. *(Optional)* Run `ssh-add ~/.ssh/<keyname>`. Replace `<keyname>` with the name you entered in Step 4.

For example, `ssh-add ~/.ssh/id_rsa`.

### 8. *(Optional)* Enter your key's passphrase.

### 8. Run `ssh-copy-id -i ~/.ssh/<keyname> <username>@<server>`. Replace `<keyname>` with your key name, `<username>` with you username in the remote server, and `<server>` with the remote server's address. Answer `yes` to all prompts.

For example, `ssh-copy-id -i ~/.ssh/id_rsa user@193.147.109.7`. You might need to enter your key's passphrase if you set one in Step 5 and didn't follow Steps 6-8.

### 9. Enter your password for the remote server.

Your public key is now uploaded to the remote server and you should be able to connect without a password.

You can test your connection by running `ssh -i ~/.ssh/<keyname> <username>@<server>` in a new terminal. You should not be prompted for a password.