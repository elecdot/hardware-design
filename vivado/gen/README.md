# vivado/gen

Temporary Vivado export artifacts go here for local PYNQ overlay use.

Expected overlay artifacts:

- `.bit` bitstream from the overlay implementation run.
- Matching `.hwh` hardware handoff from the same Block Design build.

Build artifacts in this directory are ignored by Git. Copying a `.bit` here is
useful for local testing, but do not claim an overlay is ready for PYNQ unless
the matching `.hwh` is exported with it.
