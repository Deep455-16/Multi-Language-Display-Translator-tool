# 🌍 Multi-Language Display Translator

### Automated Firmware String Translation Tool for Embedded Systems

**Multi-Language Display Translator** is a Python-based desktop GUI application designed to automate the translation and insertion of display strings in **embedded firmware `.h` files**.

Built for embedded firmware localization workflows, the tool understands the structure of `#pragma DEFSTR` and `#pragma DEFNSTR` string blocks and intelligently inserts translations while preserving **language ordering, fixed string lengths, formatting, and firmware compatibility**.

> ⚡ Translate hundreds of embedded display strings without manually editing firmware files.

---

## ✨ Features

| Feature                               | Description                                                                         |
| ------------------------------------- | ----------------------------------------------------------------------------------- |
| 🌐 **Multi-Language Translation**     | Translate firmware strings into supported languages                                 |
| 🧩 **DEFSTR / DEFNSTR Support**       | Automatically detects and processes firmware string blocks                          |
| 🧭 **Navigation-Aware Insertion**     | Inserts translations according to the language order defined inside the source file |
| 📏 **Fixed-Length Strings**           | Automatically pads or trims translations using backticks                            |
| 🆕 **New String Support**             | Add completely new English strings and generate their language blocks               |
| 🔍 **Prefix-Aware Translation**       | Preserves prefixes such as `LLS:`, `L1`, `L2`, etc.                                 |
| 🔄 **Automatic Free Slots**           | Adds empty slots automatically when a block has no remaining space                  |
| 🛡️ **Automatic Backup**              | Creates a `.bak` copy before modifying the original file                            |
| ⛔ **Safe Stop**                       | Stop a large translation job without losing already processed translations          |
| 📄 **Partial Output**                 | Saves interrupted jobs as `_partial.h`                                              |
| 🎨 **Dark GUI**                       | Clean desktop interface with progress tracking and logs                             |
| 🚀 **Parallel Processing**            | Uses worker threads to improve translation throughput                               |
| 🔁 **Translation Fallbacks**          | DeepL → Google Translate → MyMemory                                                 |
| 💾 **Persistent Configuration**       | Stores translation configuration locally                                            |
| 🧱 **Latin-1 Firmware Compatibility** | Designed around legacy embedded firmware file constraints                           |

---

## 🖥️ Application Overview

The application provides a simple workflow:

```text
Select Language
       │
       ▼
Select Firmware .h File
       │
       ▼
┌──────────────────────────┐
│ Translate & Append       │
└────────────┬─────────────┘
             │
             ▼
     Parse Firmware File
             │
             ▼
     Detect DEFSTR Blocks
             │
             ▼
       Extract English
             │
        ┌────┴────┐
        │ Exists? │
        └────┬────┘
          Yes│     │No
             │     ▼
             │  Translate
             │     │
             │     ▼
             │  Check Free Slots
             │     │
             │     ▼
             │  Determine Nav Order
             │     │
             └─────┤
                   ▼
           Insert Translation
                   │
                   ▼
          Update Navigation
                   │
                   ▼
           Generate Output
```

---

## 🧠 How It Works

The tool understands firmware files containing blocks such as:

`````````````````c
#pragma DEFSTR  'Secure Voltage````'
#pragma DEFSTR  'Säker spänning``'  // Swedish
#pragma DEFSTR  'Sichere Spannung``'  // German
#pragma DEFSTR  '````````````````'
`````````````````

The application identifies:

* The English source string
* Existing translations
* Target language
* Available placeholder slots
* Correct insertion position
* Required fixed string length

It then generates the translated entry without disturbing the rest of the firmware structure.

---

## 🧭 Intelligent Language Ordering

The translator does **not** blindly append translations to the end of a block.

Instead, it reads the **Navigation Strings** section from the firmware file:

```c
/*
Navigation Strings
Order of languages
DEFSTR  'English'
DEFSTR  'Swedish'
DEFSTR  'German'
DEFSTR  'French'
DEFSTR  'Spanish'
DEFSTR  'Italian'
DEFSTR  'Portuguese'
DEFSTR  'Danish'
*/
```

If the selected language is `Danish`, the tool determines where Danish belongs based on the navigation order.

```text
English
Swedish
German
French
Spanish
Italian
Portuguese
Danish   ← inserted here
```

This keeps the generated firmware file consistent with the existing language structure.

---

## 🌍 Supported Languages

The application currently supports languages including:

🇨🇿 Czech · 🇩🇰 Danish · 🇳🇱 Dutch · 🇫🇮 Finnish · 🇫🇷 French
🇩🇪 German · 🇭🇺 Hungarian · 🇮🇩 Indonesian · 🇮🇹 Italian · 🇳🇴 Norwegian
🇵🇱 Polish · 🇵🇹 Portuguese · 🇷🇴 Romanian · 🇷🇺 Russian · 🇪🇸 Spanish
🇸🇪 Swedish · 🇹🇷 Turkish · 🇻🇳 Vietnamese · 🇸🇦 Arabic · 🇮🇳 Hindi

> **Note:** Actual language availability and encoding behavior depend on the firmware's character-set requirements and configured translation provider.

---

## 🔄 Multi-Tier Translation Engine

The translator uses a fallback architecture to improve reliability.

```text
                 Translation Request
                         │
                         ▼
                    ┌─────────┐
                    │  DeepL  │
                    └────┬────┘
                         │
                    unavailable?
                         │
                         ▼
                ┌────────────────┐
                │ Google Translate│
                └───────┬────────┘
                        │
                   failed?
                        │
                        ▼
                ┌────────────────┐
                │    MyMemory    │
                └────────────────┘
```

### Translation Providers

**Tier 1 — DeepL**

Used when configured and supported.

**Tier 2 — Google Translate**

Used as the primary fallback through `deep-translator`.

**Tier 3 — MyMemory**

Provides an additional fallback when the previous services fail.

The application also implements request throttling and retry mechanisms to reduce translation API failures.

---

## 🧩 Prefix-Aware Translation

Firmware strings often contain technical prefixes that should not be translated.

For example:

```text
LLS:Low Level Security
```

The application separates:

```text
Prefix: LLS:
Body:   Low Level Security
```

and translates only the body:

```text
LLS:Segurança de Baixo Nível
```

The tool recognizes patterns such as:

```text
LLS: ...
L1 ...
L2 ...
L3 ...
LN ...
Ph. ...
```

This helps preserve firmware-specific identifiers and terminology.

---

## 📏 Fixed-Length Firmware Strings

Embedded firmware frequently requires strings to occupy a predetermined number of characters.

For example:

````````text
Secure Voltage```````
````````

The application automatically calculates the required length and pads the translated string using backticks:

````text
Sichere Spannung```
````

This helps prevent translated strings from breaking the expected firmware structure.

---

## 🆕 Add New Firmware Strings

The tool can also add a completely new English string.

Example:

```text
English String:
Secure Voltage

Length:
30
```

The application creates the required block using the language order defined in the firmware navigation section.

Conceptually:

`````````````````````c
#pragma DEFSTR  'Secure Voltage````````'
#pragma DEFSTR  'Swedish Translation``'  // Swedish
#pragma DEFSTR  'German Translation``'   // German
#pragma DEFSTR  'French Translation``'   // French
...
#pragma DEFSTR  '````````````````````'
#pragma DEFSTR  '````````````````````'
#pragma DEFSTR  '````````````````````'
`````````````````````

This eliminates the need to manually construct multilingual firmware blocks.

---

## 🛡️ Automatic Free-Slot Management

Every string block can contain empty placeholder slots:

`````````````````c
#pragma DEFSTR  '````````````````'
`````````````````

The translator automatically counts these slots.

**If slots are available**

The translation is inserted normally.

**If no slots are available**

The application automatically creates additional slots:

```text
No free slots
      │
      ▼
Add empty slots
      │
      ▼
Insert translation
```

There is no need for manual intervention.

---

## ⛔ Safe Translation Stop

Large firmware files can contain hundreds of strings.

The GUI provides a **STOP** button while translation is running.

When stopped:

```text
Translation stopped by user.

Translated so far: 245

Partial output:
filename_Portuguese_partial.h
```

Already processed translations are preserved instead of being discarded.

---

## 💾 Automatic Backup

Before modifying the input firmware file, the application creates:

```text
filename.h.bak
```

The translated output is written separately:

```text
filename_Portuguese.h
```

Interrupted operations produce:

```text
filename_Portuguese_partial.h
```

This provides a safer workflow for modifying firmware resources.

---

## 🖥️ GUI

The application uses a dark-themed Tkinter interface.

### Main Controls

```text
┌─────────────────────────────────────────────────────┐
│ Multi-Language Display Translator                   │
│ Embedded Firmware Localization Tool                │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Target Language   [ Portuguese              ▼ ]     │
│                                                     │
│ Input .h File     [ firmware.h ] [ Browse... ]      │
│                                                     │
│ English String    [ Optional string... ]            │
│                                                     │
│                 [ ⚡ Translate & Append ]             │
│                 [ ⛔ Stop ]                          │
│                                                     │
│ Progress ████████████████████░░░░░░  82%            │
│                                                     │
│ Output Log                                           │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Total blocks found: 682                         │ │
│ │ Already translated: 120                         │ │
│ │ Need translation: 562                           │ │
│ │ ✓ Secure Voltage → Tension sécurisée            │ │
│ │ ✓ Current → Courant                             │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

The interface provides:

* Target language selection
* Firmware file browser
* Optional English string input
* Translation progress
* Status information
* Color-coded logs
* Start/stop controls

---

## ⚙️ Technical Architecture

```text
                    ┌─────────────────────┐
                    │     Tkinter GUI     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Processing Layer  │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       File Parser       Translation Engine   Navigation
             │                 │                 │
             ▼                 ▼                 ▼
       DEFSTR Parser     DeepL / Google      Language Order
       DEFNSTR Parser    / MyMemory
             │                 │
             └────────┬────────┘
                      ▼
              String Insertion
                      │
                      ▼
               Output .h File
```

### Core Components

| Component            | Purpose                               |
| -------------------- | ------------------------------------- |
| `Tkinter`            | Desktop GUI                           |
| `ThreadPoolExecutor` | Parallel translation processing       |
| `queue.Queue`        | Thread-safe GUI updates               |
| `threading.Event`    | Translation cancellation              |
| `deep-translator`    | Translation provider interface        |
| `DeepL`              | Optional primary translation provider |
| `Google Translate`   | Translation fallback                  |
| `MyMemory`           | Secondary fallback                    |
| `re`                 | Firmware structure parsing            |
| `shutil`             | Backup generation                     |
| `JSON`               | Local configuration storage           |

---

## 📁 Project Structure

```text
Multi-Language-Display-Translator-tool/
│
├── 📄 README.md
├── 📄 .gitignore
├── 📄 get-pip.py
│
├── 📂 Documents/
│   ├── Multi_Language_Translator_PROMPT.txt
│   └── Python_to_EXE_Guide.pdf
│
└── 📂 Source_Code/
    │
    ├── Multi_Language_Translator.py
    ├── Multi_Language_Translator.spec
    ├── revert.py
    ├── get-pip.py
    ├── app.ico
    │
    ├── 📂 build/
    │   └── PyInstaller build files
    │
    └── 📂 dist/
        └── Multi_Language_Translator.exe
```

> `build/` contains generated PyInstaller artifacts and generally does not need to be committed to source control.

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd Multi-Language-Display-Translator-tool
```

### 2. Install Python

Python **3.9+** is recommended.

Verify:

```bash
python --version
```

or:

```bash
py --version
```

### 3. Install Dependencies

```bash
pip install deep-translator
```

For optional DeepL integration:

```bash
pip install deepl
```

---

## ▶️ Run the Application

Navigate to the source directory:

```bash
cd Source_Code
```

Run:

```bash
python Multi_Language_Translator.py
```

The GUI should launch automatically.

---

## 📦 Run the Windows Executable

A pre-built executable is available in:

```text
Source_Code/dist/Multi_Language_Translator.exe
```

You can launch the application directly on Windows without running the Python source manually.

---

## 🔐 DeepL Configuration

DeepL can be configured as the preferred translation provider.

The application stores its local configuration in:

```text
~/.defstr_translator_config.json
```

Example:

```json
{
  "deepl_api_key": "",
  "preferred_tier": "auto"
}
```

If a DeepL API key is not configured, the application falls back to Google Translate and MyMemory.

> ⚠️ Translation services may impose rate limits, quotas, or availability restrictions.

---

## 📊 Translation Workflow

### Existing Firmware File

```text
1. Select target language
        ↓
2. Select .h file
        ↓
3. Parse DEFSTR / DEFNSTR blocks
        ↓
4. Detect existing translation
        ↓
5. Extract English string
        ↓
6. Translate
        ↓
7. Check available slots
        ↓
8. Determine navigation position
        ↓
9. Insert translation
        ↓
10. Update navigation block
        ↓
11. Save backup
        ↓
12. Generate translated .h file
```

### New String

```text
English string
      ↓
Check whether it exists
      ↓
     No
      ↓
Ask required string length
      ↓
Generate language block
      ↓
Translate languages
      ↓
Add free slots
      ↓
Insert into firmware
      ↓
Save *_NewString.h
```

---

## 📈 Example Completion Log

A successful translation may produce output similar to:

```text
Total blocks found: 682
DEFSTR: 640
DEFNSTR: 42

Already translated: 120
Need translation: 562

✓ [DEFSTR] 'Secure Voltage'
      → 'Tension sécurisée'

✓ [DEFSTR] 'Low Level Security'
      → 'Sécurité de bas niveau'

✓ [DEFNSTR] 'Import'
      → 'Importation'

Auto free slots: added to 17 block(s)

Nav comment: updated ✓

Output: firmware_French.h
Backup: firmware.h.bak
```

---

## 🧪 Error Handling & Reliability

The application includes several mechanisms to improve reliability during large translation jobs:

* API request throttling
* Automatic retries
* Multiple translation providers
* Duplicate-language detection
* Case-insensitive language matching
* Automatic free-slot allocation
* Backup creation
* Partial output generation
* Thread-safe GUI updates
* Stop-event handling
* Prefix preservation
* Fixed-length string handling

---

## 🎯 Use Cases

This tool is particularly useful for:

* 🔌 Embedded firmware localization
* ⚡ Smart meter display translation
* 🏭 Industrial device interfaces
* 🌐 Multilingual HMI systems
* 📟 LCD/LED display strings
* 🔧 Firmware maintenance
* 🧪 Localization testing
* 📦 Large-scale firmware translation

Instead of manually editing hundreds of language entries, developers can automate the repetitive localization workflow.

---

## 🔧 Future Improvements

* [ ] Offline translation models
* [ ] Translation memory/cache
* [ ] Translation quality verification
* [ ] Side-by-side English/translated preview
* [ ] Custom language configuration
* [ ] More embedded character encodings
* [ ] Translation history
* [ ] Undo/rollback support
* [ ] Batch processing of multiple `.h` files
* [ ] Translation consistency checking
* [ ] Automated CI/CD integration
* [ ] Firmware localization validation
* [ ] Exportable translation reports

---

## 👨‍💻 Development

The application is written primarily in:

```text
Python
├── Tkinter
├── Regular Expressions
├── Threading
├── ThreadPoolExecutor
├── deep-translator
└── PyInstaller
```

Build the Windows executable using PyInstaller:

```bash
pyinstaller Multi_Language_Translator.spec
```

The generated executable will be placed in the `dist/` directory.

---

## ⚠️ Important Notes

### Firmware Encoding

The firmware workflow may rely on legacy encoding constraints. Always verify the encoding expected by your embedded firmware toolchain before integrating generated files.

### Translation Accuracy

Machine translation should be reviewed before deployment to production firmware, especially for:

* Safety messages
* Electrical terminology
* Regulatory terminology
* Technical abbreviations
* User warnings
* Device-specific terminology

### API Availability

Google Translate, DeepL, and MyMemory are external translation services. Their availability, quotas, rate limits, and terms may change independently of this application.

---

## 🏢 Developed For

**Secure Meters Ltd.**
**Embedded Firmware Team**

Designed to simplify and automate multilingual firmware display-string localization.

---

## 📜 License

Add your project's applicable license here.

For example:

```text
MIT License
```

---

## ⭐ Why This Project?

Firmware localization is often repetitive, error-prone, and difficult to maintain when hundreds of fixed-length strings and multiple language blocks are involved.

**Multi-Language Display Translator** turns that process into an automated workflow:

```text
Manual Localization
        │
        │  Hundreds of strings
        │  Manual ordering
        │  Manual padding
        │  Manual insertion
        ▼
   ❌ Time-consuming
   ❌ Error-prone
   ❌ Difficult to maintain


Multi-Language Display Translator
        │
        ▼
   Parse → Translate → Validate
        │
        ▼
   Order → Insert → Backup
        │
        ▼
   ✅ Automated
   ✅ Consistent
   ✅ Scalable
```

> **Translate once. Integrate safely. Ship multilingual firmware faster.** 🌍⚡
