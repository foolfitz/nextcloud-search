"""Eleven OCR languages on offer, three of them the default, and one image that has to agree.

Plan 16-10 put six more language packs into ``backend/Dockerfile`` (spa, ita,
nld, por, dan, est) and six more entries into ``OCR_LANGUAGE_ALLOWLIST``, and
plan 30-02 added the tenth, ces (Czech, issue #26), the same way. Issue #53
added the eleventh, chi_tra (Traditional Chinese), and with it the first name
that is not three letters and that Debian spells differently from tesseract:
the package is tesseract-ocr-chi-tra, the model chi_tra. That
is two lists in two files, and the two ways they can part company are both
silent:

* a language the reader offers but the image does not carry makes tesseract
  reject every page of every scan on that instance, and the reader cannot tell,
  because the allowlist is exactly the thing it trusts (T-03-502, T-16-36),
* a language the image installs and the build does not prove is an installation
  nobody watches: apt can succeed while the traineddata is not where tesseract
  looks for it, and the failure then appears per page, on a stranger's box.

So this file reads the Dockerfile as text, exactly like ``test_ocr_french.py``
does for the French half, and asserts both halves against the list in
``findling.config``. The list is imported and never written down a second time:
a test that repeats the set it guards agrees with itself on the very day
somebody adds an eleventh language, which is the only day it matters.

The third assertion is the other half of the decision and just as deliberate:
the default stays at three. Every additional language loads another
traineddata, which costs time and memory on every single OCR page (T-16-37).
Eleven languages available is a feature; eleven languages switched on for every
existing installation is a slowdown nobody ordered.

Since plan 18-09 the file carries a second pair, and it is the same shape of
question asked one layer up: the body languages against the OCR languages. Six
body languages are selectable since plan 18-02, three OCR languages are the
factory setting, and the two are set separately. A body language with no scanner
behind it is the Buchstabensalat trap of the phase research: the scan is read
with the wrong model, comes back as plausible looking rubbish, is indexed, is
found, and nothing anywhere says the document was never readable. One line at
startup closes it, and it is a line and never a refusal.

Not asserted here, because it is not true: that the analyzer chain and the OCR
call are the same setting. OCR turns pixels into words, the chain turns words
into terms, and an instance can legitimately want one without the other.
"""

from __future__ import annotations

import ast
import hashlib
import logging
import re
from collections.abc import Mapping
from pathlib import Path

import pytest

from findling.config import (
    OCR_DEFAULT_LANGUAGES,
    OCR_LANGUAGE_ALLOWLIST,
    SCANNERLESS_LANGUAGES,
    SUPPORTED_LANGUAGES,
    TESSERACT_NAME,
    settings,
)
from findling.main import warn_on_uncovered_languages

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"
REPO_ROOT = Path(__file__).resolve().parents[2]

# The image step for chi_tra reads a committed strip instead of drawing one
# (the font of the Czech step has no Han glyph). The generator, the strip and
# the probe are three files, and the two cases at the end hold them together.
STRIP = REPO_ROOT / "testdata" / "ocr-zh" / "probe-zh-tw.png"
STRIP_GENERATOR = REPO_ROOT / "scripts" / "dev" / "build_zh_ocr_probe.py"
CHINESE_PROBE = Path(__file__).resolve().parent / "probe_image_ocr_chinese.py"

# The one pin every language pack of this image carries. The subject of the
# assertion is the version: an unpinned pack is a different traineddata after
# the next rebuild, which is a different text in the index.
PIN = "1:4.1.0-2"

# Every apt line of a language pack, with its whole name and its whole version,
# and the pin is compared afterwards. Until issue #53 a code was three letters
# and the pattern said so. chi_tra is the first in two parts, and Debian joins
# them with a hyphen (tesseract-ocr-chi-tra) where tesseract and the allowlist
# join them with an underscore (chi_tra); _model_spelling turns the one into
# the other, so that both gates compare one spelling with one spelling.
#
# Whole names and whole versions on purpose (review of issue #53). A reader
# that only knows the shapes it expects lets every other shape through unseen:
# with a pattern for one second part, tesseract-ocr-chi-tra-vert would be
# installed without the surplus check below ever hearing of it, and a version
# matched by its prefix would take 1:4.1.0-20 for the pin.
APT_LINE = re.compile(r"tesseract-ocr-([a-z]+(?:-[a-z]+)*)=(\S+)")

# The fail closed half of the same apt block: the build asks the installed
# engine which languages it can actually see, in the model spelling, and the
# whole argument is read, so that chi_tra_vert is never taken for chi_tra.
PROVEN_LINE = re.compile(r"list-langs.*grep -qx (\S+)")

# The language whose two lines the mutation below removes. Any of the ten
# would do; spa is the first of the six that plan 16-10 added.
MUTATED_LANGUAGE = "spa"


def _dockerfile_lines() -> list[str]:
    """The Dockerfile as the build reads it, comments included."""
    return DOCKERFILE.read_text(encoding="utf-8").splitlines()


def _apt_lines(lines: list[str]) -> dict[str, str]:
    """Every language pack of the apt block with its version, commented out ones ignored.

    The Fraktur pack sits in this file as a commented example, and a reader that
    counted it would claim an image that carries a pack apt never installed.
    """
    found: dict[str, str] = {}
    for line in lines:
        if line.lstrip().startswith("#"):
            continue
        match = APT_LINE.search(line)
        if match is not None:
            found[_model_spelling(match.group(1))] = match.group(2)
    return found


def _unreadable(lines: list[str]) -> list[str]:
    """Active package lines of the apt block that the reader above cannot read.

    A package argument stands on a line of its own and starts with the package
    name. One of the language packs that APT_LINE does not match (a digit, an
    upper case letter, a missing version) would otherwise drop out of every
    comparison of this file without a word.
    """
    return [
        line
        for line in lines
        if line.strip().startswith("tesseract-ocr-")
        and APT_LINE.fullmatch(line.strip().removesuffix("\\").strip()) is None
    ]


def _installed(lines: list[str]) -> set[str]:
    """The language codes with a pinned apt line."""
    return {language for language, version in _apt_lines(lines).items() if version == PIN}


def _unpinned(lines: list[str]) -> set[str]:
    """The language codes whose apt line carries a version other than the pin."""
    return {language for language, version in _apt_lines(lines).items() if version != PIN}


def _proven_at_build_time(lines: list[str]) -> set[str]:
    """The language codes the build checks with tesseract --list-langs."""
    found: set[str] = set()
    for line in lines:
        if line.lstrip().startswith("#"):
            continue
        match = PROVEN_LINE.search(line)
        if match is not None:
            found.add(match.group(1))
    return found


def _model_spelling(package_suffix: str) -> str:
    """The language as tesseract names it, out of the name Debian gives its package."""
    return package_suffix.replace("-", "_")


def _without(lines: list[str], language: str) -> list[str]:
    """The same file with both lines of one language removed, as a mutation.

    Removed through the same two readers the gates use, so that the mutation
    takes exactly the lines that name the language and not a line that merely
    starts with its name.
    """
    kept: list[str] = []
    for line in lines:
        apt = APT_LINE.search(line)
        proven = PROVEN_LINE.search(line)
        if apt is not None and _model_spelling(apt.group(1)) == language:
            continue
        if proven is not None and proven.group(1) == language:
            continue
        kept.append(line)
    return kept


def test_every_offered_language_has_a_pinned_apt_line() -> None:
    lines = _dockerfile_lines()
    installed = _installed(lines)

    missing = set(OCR_LANGUAGE_ALLOWLIST) - installed
    assert not missing, f"the allowlist offers languages the image does not install: {missing}"

    unpinned = _unpinned(lines)
    assert not unpinned, f"these language packs are not pinned to {PIN}: {unpinned}"

    unreadable = _unreadable(lines)
    assert not unreadable, f"these apt lines are language packs the reader cannot read: {unreadable}"

    # osd is the only pack the image may carry without the allowlist naming it:
    # it is an orientation and script model, not a text language.
    surplus = installed - set(OCR_LANGUAGE_ALLOWLIST) - {"osd"}
    assert not surplus, f"the image carries language packs nothing may ever use: {surplus}"

    # The mutation, staged here rather than described: with the apt line of one
    # language gone, this case has to see it go. A gate whose red state is never
    # produced is a gate nobody has tested.
    assert MUTATED_LANGUAGE in installed
    assert MUTATED_LANGUAGE not in _installed(_without(lines, MUTATED_LANGUAGE))


def test_every_offered_language_is_proven_when_the_image_is_built() -> None:
    lines = _dockerfile_lines()
    proven = _proven_at_build_time(lines)

    unchecked = set(OCR_LANGUAGE_ALLOWLIST) - proven
    assert not unchecked, f"the build does not prove these languages arrived: {unchecked}"

    # And the same mutation from the other side.
    assert MUTATED_LANGUAGE in proven
    assert MUTATED_LANGUAGE not in _proven_at_build_time(_without(lines, MUTATED_LANGUAGE))


def test_the_default_stays_at_three_and_is_a_true_subset_of_the_offer() -> None:
    # Three, and the number is the assertion. Making all eleven the default would
    # load eight more traineddata files on every page of every scan, on every
    # instance that upgrades, in exchange for a language most of them do not
    # have. An instance that wants Spanish says so through
    # FINDLING_OCR_LANGUAGES and pays for exactly what it uses.
    assert len(OCR_DEFAULT_LANGUAGES) == 3

    # A true subset, and true in both directions: the default may never leave
    # the allowlist, because the fallback path of _ocr_languages would then hand
    # the engine a language it just refused, and the offer has to be the larger
    # of the two, or the six packs of plan 16-10 are dead weight in the layer.
    # Which three they are is the subject of backend/tests/test_ocr_french.py,
    # and one statement belongs in one file.
    assert set(OCR_DEFAULT_LANGUAGES) < set(OCR_LANGUAGE_ALLOWLIST)


def test_czech_is_accepted_in_the_admin_order_without_a_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """deu+ces, the setting issue #26 asks for, passes the allowlist untouched.

    Kept in the admin's order and without a line: a warning here would mean the
    allowlist still refuses ces and the admin would get the built in default
    back instead of Czech.
    """
    monkeypatch.setenv("FINDLING_OCR_LANGUAGES", "deu+ces")
    settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="findling"):
            chosen = settings().ocr_languages
    finally:
        settings.cache_clear()

    assert chosen == ("deu", "ces")
    assert [record for record in caplog.records if "FINDLING_OCR_LANGUAGES" in record.getMessage()] == []


def test_traditional_chinese_is_accepted_in_the_admin_order_without_a_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """chi_tra+eng, the setting docs/ocr.md recommends for Chinese scans, passes untouched.

    The Czech case above for the eleventh language (issue #53), and the first
    one whose name carries an underscore. The order is the admin's and is kept:
    chi_tra first is the order the measurement of 2026-11-15 recommends.
    """
    monkeypatch.setenv("FINDLING_OCR_LANGUAGES", "chi_tra+eng")
    settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="findling"):
            chosen = settings().ocr_languages
    finally:
        settings.cache_clear()

    assert chosen == ("chi_tra", "eng")
    assert [record for record in caplog.records if "FINDLING_OCR_LANGUAGES" in record.getMessage()] == []


def test_the_package_spelling_of_chi_tra_is_not_a_language(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """chi-tra is the name of the Debian package, and the allowlist does not guess.

    An admin who copies the package name instead of the model name gets the
    line that names the variable and the remaining languages, which is the
    answer the allowlist gives every other spelling it does not carry. A
    second accepted spelling would be a second value that has to stay in step
    with the first, on the argument list of a subprocess (T-03-502).
    """
    monkeypatch.setenv("FINDLING_OCR_LANGUAGES", "chi-tra+eng")
    settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="findling"):
            chosen = settings().ocr_languages
    finally:
        settings.cache_clear()

    assert chosen == ("eng",)
    assert [record for record in caplog.records if "FINDLING_OCR_LANGUAGES" in record.getMessage()] != []


def test_a_name_in_two_parts_is_read_in_both_spellings() -> None:
    """chi_tra is installed as tesseract-ocr-chi-tra and proven as chi_tra.

    Both readers have to report it under the allowlist spelling, or the two
    gates above would call it offered but missing and installed but unoffered
    at the same time. And the mutation, staged for this spelling as well: with
    its two lines gone, both readers have to lose it.
    """
    lines = _dockerfile_lines()
    assert "chi_tra" in _installed(lines)
    assert "chi_tra" in _proven_at_build_time(lines)

    mutated = _without(lines, "chi_tra")
    assert "chi_tra" not in _installed(mutated)
    assert "chi_tra" not in _proven_at_build_time(mutated)
    assert _installed(mutated) == _installed(lines) - {"chi_tra"}


def test_the_readers_take_whole_names_and_whole_versions() -> None:
    """Three shapes the readers must not misread, staged on lines of their own.

    A third part (chi-tra-vert) is a language of its own and not chi_tra or
    nothing, a version that only starts like the pin is not the pin, and the
    build check of chi_tra_vert is not one of chi_tra. Each was a hole of the
    first shape of these readers (review of issue #53): the surplus check would
    not have seen chi_tra_vert at all.
    """
    lines = [
        "        tesseract-ocr-chi-tra=1:4.1.0-2 \\",
        "        tesseract-ocr-chi-tra-vert=1:4.1.0-2 \\",
        "        tesseract-ocr-spa=1:4.1.0-20 \\",
        "    && tesseract --list-langs 2>&1 | grep -qx chi_tra \\",
        "    && tesseract --list-langs 2>&1 | grep -qx chi_tra_vert",
    ]
    assert _installed(lines) == {"chi_tra", "chi_tra_vert"}
    assert _unpinned(lines) == {"spa"}
    assert _proven_at_build_time(lines) == {"chi_tra", "chi_tra_vert"}

    mutated = _without(lines, "chi_tra")
    assert _installed(mutated) == {"chi_tra_vert"}
    assert _proven_at_build_time(mutated) == {"chi_tra_vert"}

    # And the line the reader cannot read at all is reported, not skipped.
    assert _unreadable(lines) == []
    odd = [
        "        tesseract-ocr-chi-Tra=1:4.1.0-2 \\",
        "        tesseract-ocr-deu2=1:4.1.0-2 \\",
        "        tesseract-ocr-chi-tra-vert \\",
    ]
    assert _unreadable([*lines, *odd]) == odd


# -- the body languages against the OCR languages ------------------------------


def _uncovered(codes: tuple[str, ...], names: Mapping[str, str]) -> set[str]:
    """The body language codes that have no tesseract name in the mapping at all."""
    return set(codes) - set(names)


def test_every_body_language_has_a_tesseract_name_and_every_name_is_installed() -> None:
    """The second parity of this file, and it is asked in both directions.

    Forwards: every code an admin can put into ``FINDLING_LANGUAGES`` has to have
    a tesseract name, or the startup warning would raise a KeyError on the one
    language it exists for. Backwards: every name in the mapping has to be a
    language this image installs, because a name outside the allowlist could
    never be covered and the warning would then be permanent and unfixable.

    Since issue #53 the forwards direction has one named exception, held here
    as exactly that: zh is a body language without a model in this image, and
    it stands in SCANNERLESS_LANGUAGES instead of TESSERACT_NAME. The two make
    up SUPPORTED_LANGUAGES exactly and do not overlap, so a code can be in
    neither only by being forgotten, and the backwards direction is untouched:
    no name outside the allowlist was put in to fill the gap.
    """
    assert _uncovered(SUPPORTED_LANGUAGES, TESSERACT_NAME) == set(SCANNERLESS_LANGUAGES)
    assert set(SCANNERLESS_LANGUAGES) <= set(SUPPORTED_LANGUAGES)
    assert SCANNERLESS_LANGUAGES.isdisjoint(TESSERACT_NAME)
    assert set(TESSERACT_NAME.values()) <= set(OCR_LANGUAGE_ALLOWLIST)

    # The staged probe, because a gate whose red state is never produced is a
    # gate nobody has tested: a further body language added to the list alone.
    assert _uncovered((*SUPPORTED_LANGUAGES, "fi"), TESSERACT_NAME) == set(SCANNERLESS_LANGUAGES) | {"fi"}


def test_the_factory_setting_needs_no_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """de and en against deu, eng and fra: every body language has its scanner.

    This is the installation nearly every admin runs, so a line here would be a
    warning on almost every start, which is a warning nobody reads.
    """
    monkeypatch.setenv("FINDLING_LANGUAGES", "de,en")
    monkeypatch.delenv("FINDLING_OCR_LANGUAGES", raising=False)
    settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="findling"):
            warn_on_uncovered_languages()
    finally:
        settings.cache_clear()

    assert caplog.records == []


def test_a_body_language_without_a_scanner_is_named_by_its_count(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Spanish in the index and not in the scanner: exactly one line, and it counts.

    The count and not the codes, which is the house rule of findling.config: a
    warning names the variable and never its value. The names are the real
    information for an admin and they travel to the admin page over GET /status,
    which plan 18-10 builds.
    """
    monkeypatch.setenv("FINDLING_LANGUAGES", "de,en,es")
    monkeypatch.setenv("FINDLING_OCR_LANGUAGES", "deu+eng")
    settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="findling"):
            warn_on_uncovered_languages()
    finally:
        settings.cache_clear()

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "FINDLING_LANGUAGES" in message
    assert " 1 " in message


def test_a_body_language_without_a_model_in_the_image_is_always_counted(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """zh against the full OCR offer: still exactly one line, and it counts one.

    SCANNERLESS_LANGUAGES of findling.config: no FINDLING_OCR_LANGUAGES can
    cover Chinese in this image, so the warning has to say so whatever the OCR
    list holds, and it must not raise on the code TESSERACT_NAME has no entry
    for. Here the OCR list carries every language the image offers, so the one
    counted language can only be zh.
    """
    monkeypatch.setenv("FINDLING_LANGUAGES", "de,en,zh")
    monkeypatch.setenv("FINDLING_OCR_LANGUAGES", "+".join(sorted(OCR_LANGUAGE_ALLOWLIST)))
    settings.cache_clear()
    try:
        assert settings().languages == ("de", "en", "zh")
        with caplog.at_level(logging.WARNING, logger="findling"):
            warn_on_uncovered_languages()
    finally:
        settings.cache_clear()

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "FINDLING_LANGUAGES" in message
    assert " 1 " in message
    assert "zh" not in message


def test_the_warning_line_carries_no_language_at_all(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Three uncovered languages, and not one of them may be readable in the line.

    Checked as a word for the two letter codes, because ``de`` sits inside
    ``model`` and a substring test would be green for the wrong reason, and as a
    substring for the three letter tesseract names, which are rare enough to be
    unambiguous.
    """
    monkeypatch.setenv("FINDLING_LANGUAGES", "es,it,pt")
    monkeypatch.setenv("FINDLING_OCR_LANGUAGES", "deu")
    settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="findling"):
            warn_on_uncovered_languages()
    finally:
        settings.cache_clear()

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert " 3 " in message
    assert [code for code in SUPPORTED_LANGUAGES if re.search(rf"\b{code}\b", message)] == []
    assert [name for name in OCR_LANGUAGE_ALLOWLIST if name in message] == []


@pytest.mark.usefixtures("volume")
def test_the_warning_refuses_nothing_and_the_container_comes_up(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The whole point of it being a warning, proven against the running lifespan.

    An instance that holds born digital Spanish files and scans nothing at all is
    perfectly healthy, so the line is a line: the container starts, the routes
    answer, and the language set it was asked for is the one it keeps.
    """
    from fastapi.testclient import TestClient

    from findling.main import APP

    monkeypatch.setenv("FINDLING_LANGUAGES", "de,en,es")
    monkeypatch.setenv("FINDLING_OCR_LANGUAGES", "deu+eng")
    settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING, logger="findling"), TestClient(APP) as client:
            answer = client.get("/heartbeat")
            active = settings().languages
    finally:
        settings.cache_clear()

    assert answer.status_code == 200
    assert active == ("de", "en", "es")
    assert [record for record in caplog.records if "FINDLING_LANGUAGES" in record.getMessage()] != []


# -- the strip of the image step for chi_tra ------------------------------------


def _constant(path: Path, name: str) -> object:
    """One module level constant, read out of the syntax tree of a script.

    Read rather than imported: the generator needs a font that no development
    machine has at that path, and the probe needs the engine of the image.
    """
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.AnnAssign | ast.Assign):
            targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                assert node.value is not None
                return ast.literal_eval(node.value)
    message = f"{name} is not defined in {path.name}"
    raise AssertionError(message)


def test_the_committed_strip_is_the_one_its_generator_names() -> None:
    """The bytes the image step reads are the bytes the generator pinned.

    A replaced picture would make the step prove something about a strip
    nobody can draw again; the generator refuses to agree with it in --check,
    and this case says so without the font.
    """
    assert hashlib.sha256(STRIP.read_bytes()).hexdigest() == _constant(STRIP_GENERATOR, "PNG_SHA256")


def test_every_word_the_probe_expects_is_on_the_strip() -> None:
    """The probe looks for words the generator drew, and only for those.

    A word that is not on the strip could never be found, and the four of five
    the probe asks for would then be four of four without anybody saying so.
    """
    sentence = _constant(STRIP_GENERATOR, "SENTENCE")
    expected = _constant(CHINESE_PROBE, "EXPECTED")
    assert isinstance(sentence, str)
    assert isinstance(expected, tuple)
    assert [word for word in expected if word not in sentence] == []
    assert _constant(CHINESE_PROBE, "REQUIRED_HITS") == len(expected) - 1
