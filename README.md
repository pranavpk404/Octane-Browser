# Octane Browser

Octane is a small desktop browsing shell built with PyQt5 and Qt WebEngine. It is not a new browser engine: it provides a focused tabbed window around the system Qt WebEngine runtime.

## Run

Python 3.10+ and a desktop environment are required. Install the Qt bindings in an isolated environment:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install PyQt5 PyQtWebEngine
python main.py
```

On Windows, activate with `.venv\Scripts\activate` instead.

The address field accepts `https://` / `http://` URLs, hostnames (which default to HTTPS), and search phrases. Use `Ctrl+L` in the Qt window to focus the field, `Ctrl+D` to bookmark the current page, `Ctrl+T` for a new tab, `Ctrl+W` to close the current tab, and `Alt+Left` / `Alt+Right` for navigation. The selected search engine is stored in `search_engine.txt` next to the application, validated against the built-in providers, and written atomically. Bookmarks and the last 200 successful page loads are stored in validated, versioned JSON files beside the application. The Library menu exposes recent bookmarks and history and can clear history.

## Verify

```sh
python -m unittest discover -p 'test_*.py'
python -m py_compile main.py browser_core.py
```

## Boundaries

- Qt WebEngine owns rendering, cookies, cache, JavaScript, and site permissions. Octane does not claim additional privacy isolation.
- The application focuses on dependable navigation, tabs, local bookmarks, and local history. Sync, downloads, and additional privacy isolation are not implemented.
- The runtime is desktop-only and requires Qt WebEngine libraries available for the host platform.
