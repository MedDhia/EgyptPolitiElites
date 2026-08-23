# Fixtures

`synthetic_volume.txt` is **not** transcribed from Politi. It is an invented
volume written to reproduce the *layout* of the annuaire — capitalised company
headers, labelled fields, and a `Conseil d'Administration` roster with French
role labels and Ottoman-Egyptian rank suffixes — so the parser can be tested
without the copyrighted scans. Company and person names in it are fictitious
and must never be treated as data.

Real name strings do appear in `tests/test_names.py`, where they exercise the
transliteration normaliser. Those are string-normalisation assertions, not
claims about anybody's directorships.
