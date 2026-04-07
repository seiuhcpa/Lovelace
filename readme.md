# ADAConnector
## Overview
`ADAConnector` is a thin client for interacting with an ADA API. It handles authentication, template creation, file uploads, processing, summary retrieval, and staging-folder housekeeping. It depends on the `requests`, `os`, `shutil`, and `json` modules.

## Initialization
Signature:
`ADAConnector(keychain=None, config=None)`

Required inputs:
- `keychain` — dict with `username` and `password`. Example:
  - `{'username': 'alice', 'password': 's3cret'}`
- `config` — dict with ADA settings. Typical keys:
  - `ada_url` (str): base ADA URL, e.g. `https://ada.example`
  - `affiliate_name` (str)
  - `data_staging_folder` (str): path to staging folder, e.g. `/tmp/ada_staging`
  - `default_template` (str): template name to use by default

On init the client obtains an access token via `obtain_token()`.

## Methods

- `obtain_token()`
  - Purpose: Authenticate and retrieve ADA access token from headers.
  - Returns: token string on success.
  - Notes: Expects endpoint `POST {ada_url}/api/users/token/access_token` with `username`/`password` as params. Handles `200`/`401`/other codes (error handling in code is minimal).

- `create_json_template(template_name)`
  - Purpose: Create a template on the ADA server using `upload-template.json` from the staging folder.
  - Params: `template_name` (str)
  - Returns: created template filename (str) when response `201`.
  - Notes: Reads `data_staging_folder/upload-template.json`. Handles `401` (prints message/details) and `403` (permission denied).

- `upload(file_path_name)`
  - Purpose: Upload a membership file (CSV recommended).
  - Params: `file_path_name` (str)
  - Returns: server filename (str) when response `201`.
  - Notes: Sends file via multipart `files`. Handles `401`/`403` responses.

- `get_blank_template()`
  - Purpose: Retrieve a new blank template.
  - Returns: `requests.Response` from `GET {ada_url}/api/template/new`.

- `clear_staging_folder(folder)`
  - Purpose: Delete files and directories in `folder`, preserving `.gitkeep`.
  - Params: `folder` (str)
  - Notes: Prints filenames and errors; uses `os.unlink` / `shutil.rmtree`.

- `get_templates()`
  - Purpose: List templates for the affiliate.
  - Returns: parsed JSON (usually a list of templates).
  - Notes: Uses authorization header.

- `process_ada_file(ada_file, template_name)`
  - Purpose: Instruct ADA to process a previously uploaded file with a template.
  - Params:
    - `ada_file` (str): file identifier/path expected by ADA
    - `template_name` (str): template identifier
  - Returns: parsed JSON on `201`.
  - Notes: Handles `400` (prints content/message/details) and `403`.

- `ada_get_summary(ada_file)`
  - Purpose: Retrieve processing summary for a file.
  - Params: `ada_file` (str)
  - Returns: parsed JSON.

- `ada_patch_summary(ada_file)`
  - Purpose: Confirm/submit processed file summary.
  - Params: `ada_file` (str)
  - Returns: parsed JSON.

- `get_default_template()`
  - Purpose: Alias to get a new template (`GET /api/template/new`).
  - Returns: `requests.Response`.

- `get_ada_template_name(template_name)`
  - Purpose: Find a template in the affiliate's template list and return a string of the form `{created}/{name}`.
  - Params: `template_name` (str)
  - Returns: formatted template name (str) or `None` if not found.

- `upload_file_to_ada(file_path_name, template_name=None)`
  - Purpose: High-level flow: upload file, choose template (default or provided), process file, get summary, and confirm.
  - Params:
    - `file_path_name` (str)
    - `template_name` (str|None)
  - Behavior:
    - Uploads file with `upload()`.
    - Resolves template: uses `config['default_template']` if present, otherwise picks the most recent.
    - Calls `process_ada_file()` then `ada_get_summary()` and `ada_patch_summary()`.
    - Prints summary and confirmation.

## Error handling & notes
- The class does minimal error handling: many branches print messages or use `pass`/`...`. Callers should check return values and HTTP status codes.
- Token is taken from response header `"x-access-token"` (assumes ADA returns token there).
- File and template name parsing uses string splits that depend on ADA response formats — validate on integration.
- Ensure `data_staging_folder` exists and contains `upload-template.json` when using `create_json_template()`.

## Example usage
Brief example creating a client and uploading a file:

```python
from Lovelace.ada_connector import ADAConnector

keychain = {'username': 'alice', 'password': 's3cret'}
config = {
    'ada_url': 'https://ada.example',
    'affiliate_name': 'ACME',
    'data_staging_folder': '/tmp/ada_staging',
    'default_template': 'MemberUpload'
}

client = ADAConnector(keychain=keychain, config=config)
client.upload_file_to_ada('/path/to/members.csv')
```
