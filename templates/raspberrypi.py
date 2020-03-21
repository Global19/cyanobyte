{% import 'macros.jinja2' as utils %}
{% import 'python.jinja2' as py %}
{% set template = namespace(enum=false, sign=false, math=false, struct=false) %}
{{ utils.pad_string('# ', utils.license(info.copyright.name, info.copyright.date, info.license.name)) -}}
#
# Auto-generated file for {{ info.title }} v{{ info.version }}.
# Generated from {{ fileName }} using Cyanobyte Codegen v{{ version }}
"""
Class for {{ info.title }}
"""
{% macro logic(logicalSteps, function) -%}

{% for step in logicalSteps %}
{% for key in step.keys() %}
{# Check if assignment is a send-op #}
{% if key == 'cmdWrite' %}
        self.set_{{step[key].register[12:].lower()}}({{step[key].value}})
        {% break %}
{%- endif %}
{# Check if assignment op #}
{% if step[key][0:1] == "=" %}
        {{key | camel_to_snake}} {{step[key]}}
{%- endif %}
{# Check if assignment is a send-op #}
{% if key == 'send' %}
        self.set_{{function.register[12:].lower()}}({{step[key]}})
{%- endif %}
{# Check if assignment is register read op #}
{% if step[key][:12] == '#/registers/' %}
        {{key | camel_to_snake}} = self.get_{{step[key][12:].lower()}}()
{%- endif %}
{# Check if assignment is function call op #}
{% if step[key][:12] == '#/functions/' %}
        {{key | camel_to_snake}} = self.{{step[key].lower() | regex_replace('#/functions/(?P<function>.+)/(?P<compute>.+)', '\\g<function>_\\g<compute>')}}()
{%- endif %}
{# If the value is a list, then this is a logical setter #}
{% if step[key] is iterable and step[key] is not string %}
        {{key | camel_to_snake}} = {{py.recursiveAssignLogic(step[key][0], step[key][0].keys()) -}}
{%- endif %}

{% endfor %}
{%- endfor %}
{%- endmacro %}

{{ py.importStdLibs(fields, functions, template) -}}
import smbus

{# Create enums for fields #}
{% if fields %}
{% for key,field in fields|dictsort %}
{% if field.enum %}
{# Create enum class #}
class {{key[0].upper()}}{{key[1:]}}Values(Enum):
    """
{{utils.pad_string("    ", "Valid values for " + field.title)}}
    """
    {% for ekey,enum in field.enum|dictsort %}
    {{ekey.upper()}} = {{enum.value}} # {{enum.title}}
    {% endfor %}
{% endif %}
{% endfor %}
{% endif %}
{% if i2c.address is iterable and i2c.address is not string %}
class DeviceAddressValues(Enum):
    """
    Valid device addresses
    """
    {% for address in i2c.address %}
    I2C_ADDRESS_{{address}} = {{address}}
    {% endfor %}
{% endif %}

{% if i2c.endian == 'little' %}
def _swap_endian(val):
    """
    Swap the endianness of a short only
    """
    return (val & 0xFF00) >> 8 | (val & 0xFF) << 8
{% endif %}

{# Add signing function if needed #}
{% for key,register in registers|dictsort %}
{% if register.signed %}
{# Optionally import class #}
{% if template.sign is sameas false %}
def _sign(val, length):
    """
    Convert unsigned integer to signed integer
    """
    if val & (1 << (length - 1)):
        return val - (1 << length)
    return val
{% set template.sign = true %}
{% endif %}
{% endif %}
{% endfor %}

class {{ info.title }}:
    """
{{utils.pad_string("    ", info.description)}}
    """
    {% if i2c.address is number %}
    device_address = {{i2c.address}}
    {% endif %}
    {% for key,register in registers|dictsort %}
    REGISTER_{{key.upper()}} = {{register.address}}
    {% endfor %}

    {% if i2c.address is iterable and i2c.address is not string %}
    def __init__(self, address):
        # Initialize connection to peripheral
        self.bus = smbus.SMBus(1)
        self.device_address = address
    {% else %}
    def __init__(self):
        # Initialize connection to peripheral
        self.bus = smbus.SMBus(1)
    {% endif %}

    {% for key,register in registers|dictsort %}
    def get_{{key.lower()}}(self):
        """
{{utils.pad_string("        ", register.description)}}
        """
        {% if register.length <= 8 %}
        val = self.bus.read_byte_data(
            self.device_address,
            self.REGISTER_{{key.upper()}}
        )
        {% elif register.length <= 16 %}
        val = self.bus.read_word_data(
            self.device_address,
            self.REGISTER_{{key.upper()}}
        )
        {% endif %}
        {% if i2c.endian == 'little' %}
        val = _swap_endian(val)
        {% endif %}
        {% if register.signed %}
        # Unsigned > Signed integer
        val = _sign(val, {{register.length}})
        {% endif %}
        return val

    def set_{{key.lower()}}(self, data):
        """
{{utils.pad_string("        ", register.description)}}
        """
        {% if i2c.endian == 'little' %}
        data = _swap_endian(data)
        {% endif %}
        {% if register.length <= 8 %}
        self.bus.write_byte_data(
            self.device_address,
            self.REGISTER_{{key.upper()}},
            data
        )
        {% elif register.length <= 16 %}
        self.bus.write_word_data(
            self.device_address,
            self.REGISTER_{{key.upper()}},
            data
        )
        {% endif %}
    {% endfor %}

    {% if fields %}
    {% for key,field in fields|dictsort %}
    {% if 'R' is in(field.readWrite) %}
    {# Getter #}

    def get_{{key.lower()}}(self):
        """
{{utils.pad_string("        ", field.description)}}
        """
        # Read register data
        # '#/registers/{{field.register[12:]}}' > '{{field.register[12:]}}'
        val = self.get_{{field.register[12:].lower()}}()
        # Mask register value
        val = val & {{utils.mask(field.bitStart, field.bitEnd)}}
        {% if field.bitEnd %}
        # Bitshift value
        val = val >> {{field.bitEnd}}
        {% endif %}
        return val
    {% endif -%}

    {%- if 'W' is in(field.readWrite) %}
    {# Setter #}

    def set_{{key.lower()}}(self, data):
        """
{{utils.pad_string("        ", field.description)}}
        """
        {% if field.bitEnd %}
        # Bitshift value
        data = data << {{field.bitEnd}}
        {% endif %}
        # Read current register data
        # '#/registers/{{field.register[12:]}}' > '{{field.register[12:]}}'
        register_data = self.get_{{field.register[12:].lower()}}()
        register_data = register_data | data
        self.set_{{field.register[12:].lower()}}(register_data)
    {% endif %}
    {% endfor %}
    {% endif %}
    {% if functions %}
    {% for key,function in functions|dictsort %}
    {% for ckey,compute in function.computed|dictsort %}
    {% if compute.input %}
    def {{key.lower()}}_{{ckey.lower()}}(self, {{py.params(compute.input)}}):
    {% else %}
    def {{key.lower()}}_{{ckey.lower()}}(self):
    {% endif %}
        """
{{utils.pad_string("        ", function.description)}}
        """
        {# Declare our variables #}
{{ py.variables(compute.variables) }}
        {# Read `value` if applicable #}
        {% if 'input' in compute %}
        {%- for vkey,variable in compute.input|dictsort %}
        {% if vkey == 'value' %}
        # Read value of register into a variable
        value = self.get_{{function.register[12:].lower()}}()
        {% endif %}
        {% endfor -%}
        {% endif %}
        {# Handle the logic #}
{{ logic(compute.logic, function) }}
        {# Return if applicable #}
        {# Return a tuple #}
        {% if compute.return is iterable and compute.return is not string %}
        return [{% for returnValue in compute.return %}{{ returnValue | camel_to_snake }}{{ ", " if not loop.last }}{% endfor %}]
        {% endif %}
        {# Return a plain value #}
        {% if compute.return is string %}
            {# See if we need to massage the data type #}
            {% if compute.output == 'int16' %}
        # Convert from a unsigned short to a signed short
        {{compute.return}} = struct.unpack("h", struct.pack("H", {{compute.return}}))[0]
            {% endif %}
        return {{compute.return}}
        {% endif %}
    {% endfor %}
    {% endfor %}
    {% endif %}