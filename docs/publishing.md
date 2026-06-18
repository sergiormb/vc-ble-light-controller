# Publishing

VC BLE Light Controller is published from GitHub Actions.

## Repository

- Source repository: `https://github.com/sergiormb/vc-ble-light-controller`
- APT repository: `https://sergiormb.github.io/vc-ble-light-controller/`
- APT branch: `gh-pages`

## GitHub Secrets

The release workflow needs a dedicated GPG key for signing the APT repository:

- `APT_GPG_PRIVATE_KEY`: ASCII-armored private key.
- `APT_GPG_KEY_ID`: key fingerprint or long key id.

Create a dedicated key:

```bash
gpg --batch --quick-generate-key "VC BLE Light Controller APT Repository <sergiormb@users.noreply.github.com>" rsa4096 sign 2y
gpg --armor --export-secret-keys KEY_ID
gpg --armor --export KEY_ID
```

Only the public key is published to GitHub Pages as
`vc-ble-light-controller-archive-keyring.gpg`.

## Release Flow

1. Update `src/raingel/__init__.py` and `pyproject.toml` if the version changes.
2. Run local checks:

   ```bash
   python3 -m pytest
   python3 -m compileall -q src tests
   ./scripts/build-deb.sh
   ```

3. Commit and push to `main`.
4. Create and push a tag:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

The `Release` workflow builds the `.deb`, attaches it to a GitHub Release,
generates signed APT metadata, and publishes the apt repository to `gh-pages`.
