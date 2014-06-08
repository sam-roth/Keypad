


def main():
    import sys
    import logging
    logfmt = '[%(asctime)s|%(module)s:%(lineno)d|%(levelname)s]\n  %(message)s'

    logging.basicConfig(level=logging.DEBUG,
                        format=logfmt)
    import os.path
    thirdparty = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, 'third-party'))
    import sys
    sys.path.insert(0, thirdparty)
    from . import config, options
#     import importlib
#     importlib.import_module(options.DefaultDriverMod).main()
    from .qt import driver

    # allow for sending a commandline command at startup
    if len(sys.argv) > 2 and sys.argv[1] == '-c':
        from .core.notification_queue import run_in_main_thread
        from .control.command_line_interpreter import CommandLineInterpreter
        from .abstract.application import app, AbstractApplication
        from .core.errors import NoSuchCommandError

        interp = CommandLineInterpreter()

        def win_creation_hook(win):
            # responder chain may not be updated yet
            try:
                interp.exec(app(), sys.argv[2])
            except NoSuchCommandError:
                interp.exec(win, sys.argv[2])
            finally:
                app().window_created.disconnect(win_creation_hook)

        def app_creation_hook(_):
            app().window_created.connect(win_creation_hook)


        AbstractApplication.application_created.connect(app_creation_hook)


    driver.main()

if __name__ == '__main__':
    main()
