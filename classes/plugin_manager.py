"""
Plugin Manager

"""
import os
import importlib.util
from dotenv import load_dotenv

load_dotenv()
activate_plugin = os.getenv("ENABLE_PLUGINS", None)

class PluginManager:
    """
    Plugin Manager class.

    This class is used to load and manage plugins. A plugin is a python file
    in the plugin directory. Each plugin is loaded and its init function is called.
    The plugin is then saved in an object (a dictionary) so that its functions can be
    later applied via apply_filters or apply_filters_async.
    """
    def __init__(self, plugin_dir='plugins'):
        self.plugin_dir = plugin_dir
        self.plugins = {}  # Dizionario per salvare i plugin caricati

    def init_plugins(self, plugin_dir='plugins'):
        """
        Initialize plugins from the specified directory.

        This function scans the given directory for Python files (.py),
        loads each file as a module, executes its 'init' function if available,
        and saves the plugin module in the self.plugins dictionary.
        """
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)

        for plugin_file in os.listdir(plugin_dir):
            if plugin_file.endswith('.py'):
                plugin_name = plugin_file[:-3]
                plugin_path = os.path.join(plugin_dir, plugin_file)
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                plugin = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin)
                if hasattr(plugin, 'init'):
                    try:
                        plugin.init()
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        print(f"Error initializing plugin {plugin_name}: {e}")
                # Salva il plugin caricato nell'oggetto
                self.plugins[plugin_name] = plugin

    def load_plugin(self, plugin_name):
        """
        Load a plugin by its name.

        Args:
            plugin_name (str): The name of the plugin to load.

        Returns:
            module: The loaded plugin module from the internal dictionary,
            or None if the plugin does not exist or plugins are disabled.
        """
        if activate_plugin is None:
            return None
        return self.plugins.get(plugin_name, None)

    def apply_filters(self, function_name, value):
        """
        Apply a sequence of filter functions from plugins to a given value.

        This method iterates through all the loaded plugins (saved in self.plugins),
        checks if the specified function exists within the plugin,
        and applies it to the input value.

        Args:
            function_name (str): The name of the function to apply from each plugin.
            value: The initial value to be filtered.

        Returns:
            The value after being processed by all applicable plugin functions.
        """
        if activate_plugin is None:
            if value is not None:
                return value
            return None

        for plugin in self.plugins.values():
            if hasattr(plugin, function_name):
                filter_function = getattr(plugin, function_name)
                value = filter_function(value)
        return value

    async def apply_filters_async(self, function_name, value):
        """
        Asynchronously apply a sequence of filter functions from plugins to a given value.

        This method iterates through all the loaded plugins (saved in self.plugins),
        checks if the specified function exists within the plugin,
        and applies it to the input value asynchronously.

        Args:
            function_name (str): The name of the function to apply from each plugin.
            value: The initial value to be filtered.

        Returns:
            The value after being processed by all applicable plugin functions.
        """
        if activate_plugin is None:
            if value is not None:
                return value
            return None

        for plugin in self.plugins.values():
            if hasattr(plugin, function_name):
                filter_function = getattr(plugin, function_name)
                value = await filter_function(value)
        return value
