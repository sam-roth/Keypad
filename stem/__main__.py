

def _setup_logging():
    import logging
    logfmt = '[%(asctime)s|%(module)s:%(lineno)d|%(levelname)s]\n  %(message)s'

    logging.basicConfig(level=logging.DEBUG,
                        format=logfmt)

def main():
    _setup_logging() # needs to be done before using the logger

    import sys, sip, os.path
    from . import config, options
    from .qt import driver


    # As for memory, modern OSes handle that just fine, so we don't need to free
    # memory on exiting. The GC does this in a non-deterministic order, which can
    # cause SEGVs. Other resources may be left open by this, but it's generally
    # not okay to rely on GC for those anyway, so we shouldn't be any worse off.
    sip.setdestroyonexit(False) 

    # Add the `third-party` dir into the path.
    thirdparty = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                              os.path.pardir,
                                              'third-party'))
    sys.path.insert(0, thirdparty)

    # Allow for sending a commandline command at startup.
    if len(sys.argv) > 2 and sys.argv[1] == '-c':
        from .core.notification_queue import run_in_main_thread
        from .control.command_line_interpreter import CommandLineInterpreter
        from .abstract.application import app, AbstractApplication
        from .core.errors import NoSuchCommandError

        interp = CommandLineInterpreter()

        def win_creation_hook(win):
            # Responder chain may not be updated yet.
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
