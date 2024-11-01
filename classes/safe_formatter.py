from string import Formatter
class SafeFormatter(Formatter):
        def get_field(self, field_name, args, kwargs):
            if '.' in field_name or '[' in field_name:
                raise Exception('Invalid format string.')
            return super().get_field(field_name,args,kwargs)