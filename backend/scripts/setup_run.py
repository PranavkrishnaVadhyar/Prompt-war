"""Run an explicit setup command without leaking credentials through tracebacks."""
import runpy
import sys


if __name__ == '__main__':
    allowed = {'create_tables', 'bootstrap_organiser', 'import_questions'}
    if len(sys.argv) < 2 or sys.argv[1] not in allowed:
        raise SystemExit('Choose create_tables, bootstrap_organiser or import_questions.')
    command = sys.argv.pop(1)
    try:
        runpy.run_module('scripts.' + command, run_name='__main__')
    except Exception as error:
        print('Setup command failed (' + type(error).__name__ + '); sensitive error details withheld.')
        raise SystemExit(1)
