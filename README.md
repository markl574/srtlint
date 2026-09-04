# srtlint

A command-line checker for `.srt` subtitle files.

Most tools that consume SRT files (video players, ffmpeg, streaming
platforms) are forgiving about the format: they'll play a file with
out-of-order indices, overlapping timestamps, or a stray blank cue without
complaining. That's fine until the file goes through an automated pipeline
(muxing, translation, re-timing) where a small structural problem turns into
a subtitle that's silently wrong or missing. srtlint checks the structure of
an SRT file and fails loudly on anything questionable, so problems get
caught before they reach a pipeline instead of after.

## What it checks

- cue indices are integers, sequential, and start at 1
- timecodes are in exact `HH:MM:SS,mmm --> HH:MM:SS,mmm` form
- each cue's end time is after its start time
- cues appear in non-decreasing start-time order
- every cue has non-empty text
- the file has no byte-order mark

By default all of these are hard errors. Real-world SRT files break several
of these rules routinely (non-sequential indices from manual edits, a period
instead of a comma in the timecode, one file concatenated from two others
with overlapping times). Pass `--lenient` to turn recoverable problems into
warnings instead of failures — the file still gets parsed and checked, it
just doesn't stop the run.

## Usage

```
$ srtlint movie.srt
movie.srt: ok (142 cues)

$ srtlint movie.srt
movie.srt: line 87: expected index 43, got 44
$ echo $?
1

$ srtlint --lenient movie.srt
movie.srt: warning: line 87: expected index 43, got 44
movie.srt: ok (142 cues)
```

Multiple files can be checked in one run; the exit code is 1 if any file
failed.

## Installing

No dependencies, standard library only. Run directly:

```
$ python -m srtlint.cli movie.srt
```

or install the entry point:

```
$ pip install -e .
$ srtlint movie.srt
```

## Status

Early skeleton: parsing and the checks above work. Not yet covered: SRT
writing/reformatting, encoding detection beyond UTF-8, WebVTT support.
