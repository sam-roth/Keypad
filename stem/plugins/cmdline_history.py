

from stem.api import Plugin, register_plugin, Config
from stem.control.command_line_interaction import CommandLineInteractionMode
from stem.options import GeneralSettings


@register_plugin
class CommandLineHistoryPlugin(Plugin):

    author = 'Sam Roth'
    version = '2014.06.1'
    name = 'Command Line History'


    def attach(self):
        settings = GeneralSettings.from_config(Config.root)

        if not settings.user_config_home.exists():
            settings.user_config_home.mkdir(parents=True)
        self.histpath = settings.user_config_home / 'cmdline_history'

        CommandLineInteractionMode.created.connect(self._on_clim_created)

    def detach(self):
        CommandLineInteractionMode.created.disconnect(self._on_clim_created)

    def _on_clim_accepted(self, im):
        assert isinstance(im, CommandLineInteractionMode)

        hist = im.command_history
        if hist:
            with self.histpath.open('a') as f:
                f.write(hist[-1] + '\n')

    def _on_clim_created(self, im):
        assert isinstance(im, CommandLineInteractionMode)
        im.accepted.connect(self._on_clim_accepted, add_sender=True)

        try:
            with self.histpath.open('r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        im.push_history_item(line)
        except IOError:
            pass





