def clean_code(code: str) -> str:
    return code.strip().replace('\r\n', '\n')


def detect_language(filename: str) -> str:
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return {
        'py':   'python',
        'ts':   'typescript',
        'tsx':  'typescript',
        'js':   'javascript',
        'jsx':  'javascript',
        'go':   'go',
        'rs':   'rust',
        'java': 'java',
        'rb':   'ruby',
        'cs':   'csharp',
        'cpp':  'cpp',
        'c':    'c',
        'php':  'php',
        'kt':   'kotlin',
        'swift':'swift',
    }.get(ext, 'unknown')


def truncate_code(code: str, max_chars: int = 8000) -> str:
    if len(code) <= max_chars:
        return code
    half = max_chars // 2
    removed = len(code) - max_chars
    return (
        code[:half]
        + f"\n\n# ... [{removed} characters truncated — file too large] ...\n\n"
        + code[-half:]
    )


def format_code_block(code: str, language: str) -> str:
    return f"```{language}\n{code}\n```"


def count_lines(code: str) -> int:
    return len(code.splitlines())