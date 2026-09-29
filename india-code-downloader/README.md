# India Code Legislation Downloader

This script downloads Acts from **India Code** (https://www.indiacode.nic.in) and saves
them as **UTF-8 text files**, laid out like this:

- **Each legislation is a folder.**
- **Each section is a separate `.txt` file** that holds the text of that section.

```
Legislations/                                   <- your OUTPUT_PATH
├── The Indian Contract Act, 1872/
│   ├── Section_001 - Sec 1 - Short title, extent and commencement.txt
│   ├── Section_002 - Sec 2 - Interpretation-clause.txt
│   └── ...
├── The Specific Relief Act, 1963/
│   ├── Section_001 - Sec 1 - Short title, extent and commencement.txt
│   └── ...
└── The Limitation Act, 1963/
    └── ...
```

Each section file looks like this:

```
The Indian Contract Act, 1872
Section 1: Short title, extent and commencement
Source: https://www.indiacode.nic.in/show-data?actid=...&sectionId=...

<full text of the section>

----- Footnotes -----
<footnotes, if any>
```

---

## What's in this zip

| File | What it is |
|---|---|
| `download_legislation.py` | The script. **This is the only file you edit.** |
| `requirements.txt` | The two Python packages the script needs |
| `run_windows.bat` | Double-click to run on Windows |
| `run_mac_linux.sh` | Run on Mac or Linux |
| `README.md` | This guide |

---

## Step 1: Install Python (one time only)

1. Go to https://www.python.org/downloads/ and download Python 3.9 or newer.
2. **Windows:** on the first installer screen, tick **"Add Python to PATH"**, then click Install.
3. To check it worked, open a terminal (Windows: **Command Prompt**; Mac: **Terminal**) and type:
   ```
   python --version
   ```
   (On Mac use `python3 --version`.) You should see something like `Python 3.12.x`.

## Step 2: Unzip the folder

Unzip `india-code-downloader.zip` anywhere, for example your Desktop or Documents.

## Step 3: Set the output path (where files are saved)

Open `download_legislation.py` in any text editor (Notepad, VS Code, TextEdit, etc.).
Near the top you'll find:

```python
OUTPUT_PATH = r""
```

Put the full path of your folder between the quotes. **Keep the `r` in front.**

```python
# Windows
OUTPUT_PATH = r"C:\Users\Karthik\Documents\Legislations"

# Mac
OUTPUT_PATH = r"/Users/karthik/Documents/Legislations"
```

- If the folder doesn't exist yet, the script creates it.
- If you leave it empty (`r""`), the files go into a `downloaded_legislations` folder
  next to the script.

**How to copy a folder path:**
- Windows: open the folder in File Explorer, click the address bar, and copy it.
- Mac: right-click the folder in Finder, hold **Option**, and choose **"Copy … as Pathname"**.

## Step 4: Choose which legislations to download

Just below the output path is the list of legislations:

```python
LEGISLATIONS = [
    {"name": "The Indian Contract Act, 1872"},
    {"name": "The Specific Relief Act, 1963"},
    {"name": "The Limitation Act, 1963"},
]
```

- **To change a legislation,** replace the name inside the quotes.
- **To add one,** add another line in the same format. Keep the comma at the end.
- **To remove one,** delete its line.
- The name you type is also used as the folder name.

### More reliable: add the India Code link

With only a name, the script searches India Code and picks the closest match. If it picks
the wrong Act, or can't find one, give it the exact link:

1. Open https://www.indiacode.nic.in and search for the Act.
2. Open the Act's page and copy the link from the browser's address bar. It looks like
   `https://www.indiacode.nic.in/handle/123456789/XXXX` (XXXX is a number).
3. Add it as `"url"`:

```python
LEGISLATIONS = [
    {"name": "The Indian Contract Act, 1872",
     "url":  "https://www.indiacode.nic.in/handle/123456789/XXXX"},
    {"name": "The Limitation Act, 1963"},     # name-only still works
]
```

Save the file after editing.

## Step 5: Run it

**Windows:** double-click **`run_windows.bat`**.

**Mac / Linux:** open Terminal in the folder and run:
```
bash run_mac_linux.sh
```

**Or run it by hand** (any system), from inside the unzipped folder:
```
pip install -r requirements.txt
python download_legislation.py
```
(On Mac use `pip3` and `python3`.)

The script prints its progress section by section and shows a summary at the end.
A large Act with hundreds of sections can take several minutes, because the script waits
about 1 second between requests so it doesn't overload the government server.

---

## Optional settings

These are in section 3 of `download_legislation.py`. You usually don't need to change them.

| Setting | Default | Meaning |
|---|---|---|
| `DELAY_BETWEEN_REQUESTS` | `1.0` | Seconds to wait between requests |
| `REQUEST_TIMEOUT` | `60` | Seconds before a request gives up |
| `MAX_RETRIES` | `4` | How many times to retry a failed request |
| `VERIFY_SSL` | `True` | Set to `False` only if you get SSL certificate errors |
| `SKIP_EXISTING_FILES` | `True` | Re-running skips sections that are already downloaded, so an interrupted run carries on where it stopped |
| `INCLUDE_FOOTNOTES` | `True` | Adds the section's footnotes (amendment notes) at the end of each file |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Python isn't on PATH. Reinstall it with **"Add Python to PATH"** ticked, or try `py` instead of `python`. |
| `Missing packages` | Run `pip install -r requirements.txt` |
| `SSLError` / certificate error | Set `VERIFY_SSL = False` in the script |
| `Could not find this Act` or the wrong Act is downloaded | Add the Act's `"url"` as shown in Step 4 |
| `No sections found on the Act page` | Some older Acts are on India Code as a PDF only, with no section-wise text. Check the Act's page in your browser. If it has no section list, this script can't split it. |
| Timeouts or connection errors | India Code is sometimes slow. Run the script again; finished sections are skipped. You can also raise `REQUEST_TIMEOUT` or `DELAY_BETWEEN_REQUESTS`. |
| Some section files say `[No text returned by India Code]` | India Code has no text for that section (often a repealed or omitted section). |

## How it works (technical)

India Code has no official public API, so the script uses the same web endpoints that the
India Code website itself uses:

1. **Find the Act:** `GET /simple-search?query=<name>` returns search results. The script
   picks the best `/handle/123456789/<id>` link. This step is skipped if you give a `"url"`.
2. **List the sections:** it opens the Act page (`/handle/...?view_type=browse`) and collects
   every section link (`/show-data?actid=…&sectionId=…&sectionno=…&orderno=…`).
3. **Get each section's text:** `GET /SectionPageContent?actid=…&sectionID=…` returns JSON
   with the section's `content` and `footnote` as HTML. If that fails, the script reads the
   section page directly.
4. **Save:** the HTML is turned into clean plain text and written as a UTF-8 `.txt` file,
   one file per section, in a folder named after the legislation.

If India Code changes its website layout, steps 2 and 3 are the parts that may need updating.
