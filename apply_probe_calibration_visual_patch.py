from pathlib import Path

# Temporary safety no-op: the previous probe-calibration visual override used
# a DOM observer that could repeatedly react to its own style changes and lock
# up the client. Keep the build step in place but do not inject that script.
print('Probe calibration visual override disabled to keep the app responsive')
