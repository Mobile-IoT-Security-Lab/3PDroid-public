#!/usr/bin/env python
# coding: utf-8

import logging
import re
from xml.dom import minidom

from androguard.core.analysis.analysis import Analysis, FieldClassAnalysis
from androguard.core.bytecodes.apk import AXMLPrinter, APK
from androguard.core.bytecodes.dvm import ClassDefItem, Instruction
from androguard.misc import AnalyzeAPK


def parse_const(instruction: Instruction):
    if instruction.get_name() == 'const':
        return hex(instruction.get_literals().pop())
    elif instruction.get_name() == 'const/high16':
        return hex(instruction.get_literals().pop()) + '0' * 4
    else:
        raise Exception('Unrecognized instruction {0}'.format(instruction.get_name()))


def get_field_refs(resource_id_classes):
    field_refs = {}
    # Populate field_refs with field id as key and field reference as value.
    for resource_id in resource_id_classes:
        for field in resource_id.get_fields():
            field_id = hex(field.get_init_value().get_value())
            field_refs[field_id] = field
    return field_refs


class TextField(object):

    type_mask_class = 0x0000000f
    type_mask_variation = 0x00000ff0

    type_class_lookup = {
        0x00000000: 'TYPE_NULL',
        0x00000001: 'TYPE_CLASS_TEXT',
        0x00000002: 'TYPE_CLASS_NUMBER',
        0x00000003: 'TYPE_CLASS_PHONE',
        0x00000004: 'TYPE_CLASS_DATETIME'
    }

    type_variation_lookup = {
        'TYPE_NULL': {},
        'TYPE_CLASS_TEXT': {
            0x00: 'TYPE_TEXT_VARIATION_NORMAL',
            0x10: 'TYPE_TEXT_VARIATION_URI',
            0x20: 'TYPE_TEXT_VARIATION_EMAIL_ADDRESS',
            0x30: 'TYPE_TEXT_VARIATION_EMAIL_SUBJECT',
            0x40: 'TYPE_TEXT_VARIATION_SHORT_MESSAGE',
            0x50: 'TYPE_TEXT_VARIATION_LONG_MESSAGE',
            0x60: 'TYPE_TEXT_VARIATION_PERSON_NAME',
            0x70: 'TYPE_TEXT_VARIATION_POSTAL_ADDRESS',
            0x80: 'TYPE_TEXT_VARIATION_PASSWORD',
            0x90: 'TYPE_TEXT_VARIATION_VISIBLE_PASSWORD',
            0xa0: 'TYPE_TEXT_VARIATION_WEB_EDIT_TEXT',
            0xb0: 'TYPE_TEXT_VARIATION_FILTER',
            0xc0: 'TYPE_TEXT_VARIATION_PHONETIC',
            0xd0: 'TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS',
            0xe0: 'TYPE_TEXT_VARIATION_WEB_PASSWORD'
        },
        'TYPE_CLASS_NUMBER': {
            0x00: 'TYPE_NUMBER_VARIATION_NORMAL',
            0x10: 'TYPE_NUMBER_VARIATION_PASSWORD'
        },
        'TYPE_CLASS_PHONE': {},
        'TYPE_CLASS_DATETIME': {
            0x00: 'TYPE_DATETIME_VARIATION_NORMAL',
            0x10: 'TYPE_DATETIME_VARIATION_DATE',
            0x20: 'TYPE_DATETIME_VARIATION_TIME'
        }
    }

    def __init__(self, field_id: str, field_name: str, field_type: str, reference, tainted_field=None,
                 is_password=False):
        self.id = field_id
        self.name = field_name
        self.type = field_type
        self.ref = reference

        # Holds some information about the field in the code (e.g., the XREFs with the usage of the field).
        self.tainted_field = tainted_field

        self.is_password = is_password

        self.type_class = self.get_type_class()
        self.type_variation = self.get_type_variation()

        if self.type_variation and 'password' in self.type_variation.lower():
            self.is_password = True

    def get_type_class(self):
        if not self.type:
            return 'NO_TYPE'
        type_class = int(self.type, 16) & self.type_mask_class
        if type_class in self.type_class_lookup:
            return self.type_class_lookup[type_class]
        else:
            return 'TYPE_CLASS_NOT_RECOGNIZED'

    def get_type_variation(self):
        if not self.type:
            return None
        type_variation = int(self.type, 16) & self.type_mask_variation
        if self.type_class in self.type_variation_lookup and \
                type_variation in self.type_variation_lookup[self.type_class]:
            return self.type_variation_lookup[self.type_class][type_variation]
        else:
            return None

    def __str__(self):
        if self.tainted_field:
            return 'name: {0} ({1} in code); id: {2}; type: {3}; variation: {4}; password: {5}'.format(
                self.name, self.tainted_field.get_field().get_name(), self.id, self.type_class, self.type_variation,
                self.is_password)
        else:
            return 'name: {0}; id: {1}; type: {2}; variation: {3}; password: {4}'.format(
                self.name, self.id, self.type_class, self.type_variation, self.is_password)


class SmartInput(object):

    default = '123456'

    type_class = {
        'TYPE_NULL': '',
        'TYPE_CLASS_TEXT': 'example',
        'TYPE_CLASS_NUMBER': '1',
        'TYPE_CLASS_PHONE': '3453453456',
        'TYPE_CLASS_DATETIME': '03032015'
    }

    type_variation = {
        'TYPE_TEXT_VARIATION_NORMAL': 'example',
        'TYPE_TEXT_VARIATION_URI': 'https://www.example.com',
        'TYPE_TEXT_VARIATION_EMAIL_ADDRESS': 'john@example.com',
        'TYPE_TEXT_VARIATION_EMAIL_SUBJECT': 'Example Email Subject',
        'TYPE_TEXT_VARIATION_SHORT_MESSAGE': 'Example Short Message',
        'TYPE_TEXT_VARIATION_LONG_MESSAGE': 'This is an example of a very long message for an input text.',
        'TYPE_TEXT_VARIATION_PERSON_NAME': 'John Smith',
        'TYPE_TEXT_VARIATION_POSTAL_ADDRESS': '16100',
        'TYPE_TEXT_VARIATION_PASSWORD': 'pa$$w0rd',
        'TYPE_TEXT_VARIATION_VISIBLE_PASSWORD': 'pa$$w0rd',
        'TYPE_TEXT_VARIATION_WEB_EDIT_TEXT': '',
        'TYPE_TEXT_VARIATION_FILTER': '',
        'TYPE_TEXT_VARIATION_PHONETIC': '',
        'TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS': 'john@example.com',
        'TYPE_TEXT_VARIATION_WEB_PASSWORD': 'pa$$w0rd',

        'TYPE_NUMBER_VARIATION_NORMAL': '3453453456',
        'TYPE_NUMBER_VARIATION_PASSWORD': '4321',

        'TYPE_DATETIME_VARIATION_NORMAL': '03032015',
        'TYPE_DATETIME_VARIATION_DATE': '03032015',
        'TYPE_DATETIME_VARIATION_TIME': '000000'
    }

    def __init__(self, apk_path: str):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.logger.info('Smart input generation')

        self.smart_inputs = {}

        self.apk: APK = None
        self.dx: Analysis = None

        self.apk, _, self.dx = AnalyzeAPK(apk_path)

        tmp_edit_text_classes = self.get_subclass_names('Landroid/widget/EditText;')

        # Convert EditText classes to dot notation ('EditText' is a built-in class so the prefix is not needed).
        # This notation will be used when looking for text inputs in the xml layout files.
        self.edit_text_classes = {'EditText'}
        for clazz in tmp_edit_text_classes:
            self.edit_text_classes.add(re.search('L(.*);', clazz).group(1).replace('/', '.'))

        try:
            self.class_object_list = [clazz.get_vm_class() for clazz in self.dx.get_internal_classes()]

            self.classes_dict = self.get_class_dict()

            # Find the R$id classes.
            self.resource_ids = self.get_resource_ids(self.class_object_list)

            # Find the R$layout classes.
            self.resource_layouts = self.get_resource_layouts(self.class_object_list)

            self.field_refs = get_field_refs(self.resource_ids)

            self.find_text_fields()
        except Exception as e:
            self.logger.error('Error during smart input generation: {0}'.format(e))
            raise

    def get_subclass_names(self, class_name: str):
        subclass_names = set()
        edit_text_class = self.dx.get_class_analysis(class_name)
        if edit_text_class:
            for clazz in edit_text_class.get_xref_from():
                if clazz.get_vm_class().get_superclassname() == class_name:
                    subclass_name = clazz.get_vm_class().get_name()
                    subclass_names.add(subclass_name)
                    subclass_names.update(self.get_subclass_names(subclass_name))
        return subclass_names

    # Return a dict with the class names and the class objects.
    def get_class_dict(self):
        classes = {}
        for clazz in self.class_object_list:
            # Get the name of the class using the dot notation.
            clazz_name = re.search('L(.*);', clazz.get_name()).group(1).replace('/', '.')
            classes[clazz_name] = clazz

        return classes

    # Get R$id classes.
    def get_resource_ids(self, classes):
        resource_ids = []
        for clazz in classes:
            if clazz.get_name().endswith('R$id;'):
                self.logger.debug('Found R$id class at {0}'.format(clazz.get_name()))
                resource_ids.append(clazz)
        return resource_ids

    # Get R$layout classes.
    def get_resource_layouts(self, classes):
        resource_layouts = []
        for clazz in classes:
            if clazz.get_name().endswith('R$layout;'):
                self.logger.debug('Found R$layout class at {0}'.format(clazz.get_name()))
                resource_layouts.append(clazz)
        return resource_layouts

    def get_xml_from_file(self, xml_file):
        ap = AXMLPrinter(self.apk.get_file(xml_file))
        return minidom.parseString(ap.get_buff())

    # Return every instance of an EditText field and their inputType in the XML.
    # Not all EditText fields will have an inputType specified in the XML.
    def get_input_fields_with_input_types_from_xml(self, xml_file):
        input_fields = {}
        xml_content = self.get_xml_from_file(xml_file)
        for edit_text_tag in self.edit_text_classes:
            for item in xml_content.getElementsByTagName(edit_text_tag):
                android_id = None
                input_type = {
                    'type': None,
                    'is_password': False
                }
                for k, v in item.attributes.itemsNS():
                    if k[1] == 'id':
                        android_id = v[1:]
                    if k[1] == 'inputType':
                        input_type['type'] = v
                    if k[1] == 'password':
                        # Deprecated, only inputType should be used, but some apps still use this.
                        input_type['is_password'] = True if v.lower() == 'true' else False

                if android_id:
                    input_fields[hex(int(android_id, 16))] = input_type

        return input_fields

    def parse_move(self, bc, index):
        i = bc.get_instruction(index)
        register = i.get_output().split(',')[1].strip()
        for x in range(index - 1, -1, -1):
            i = bc.get_instruction(x)
            if 'const' in i.get_name() and register in i.get_output():
                return parse_const(bc.get_instruction(x))

    def get_activity_xml(self, activity_class):
        # Build a list of every layout hex value referenced in activity's bytecode.
        hex_codes = []
        for method in activity_class.get_methods():
            if method.get_name() == 'onCreate':
                try:
                    for index, instruction in enumerate(method.get_instructions()):
                        # Find setContentView, then parse the passed value from the previous
                        # const or const/high16 instruction.
                        if 'setContentView' in instruction.show_buff(0):
                            instruction = method.get_code().get_bc().get_instruction(index - 1)
                            if 'const' in instruction.get_name():
                                hex_codes.append(parse_const(instruction))
                            elif 'move' in instruction.get_name():
                                hex_codes.append(self.parse_move(method.get_code().get_bc(), index - 1))
                except Exception:
                    pass

        # Cross check the list of hex codes with R$layout to retrieve XML layout file name.
        for layout in self.resource_layouts:
            for field in layout.get_fields():
                if hex(field.get_init_value().get_value()) in hex_codes:
                    return 'res/layout/{0}.xml'.format(field.get_name())

        return None

    def get_input_field_from_code(self, class_object: ClassDefItem, field_id: str):
        self.logger.debug('Analyzing field {0}'.format(field_id))

        for method in class_object.get_methods():
            instructions = iter(method.get_instructions())
            for instruction in instructions:
                if ('const' == instruction.get_name() or 'const/high16' == instruction.get_name()) \
                        and field_id == parse_const(instruction):
                    # Get the register in which the constant is assigned.
                    register = instruction.get_output().split(',')[0].strip()

                    while True:
                        try:
                            last_instruction = instruction
                            instruction = next(instructions)
                        except StopIteration:
                            self.logger.debug('Could not get input field {0} from code'.format(field_id))
                            return None

                        # Follow the register to the next invoke-virtual of findViewById...
                        if (register in instruction.get_output() and 'findViewById' in instruction.get_output()) \
                                and 'invoke-virtual' in instruction.get_name():
                            # ...and get the register of that output.
                            register = instruction.get_output().split(',')[1].strip()

                        elif instruction.get_name() == 'move-result-object' and \
                                'invoke-virtual' in last_instruction.get_name():
                            register = instruction.get_output().strip()

                        elif (instruction.get_name() == 'iput-object' or instruction.get_name() == 'sput-object') and \
                                register in instruction.get_output().split(',')[0].strip():
                            out_sp = re.search(r'.*, (.*)->(\b[\w]*\b) (.*)', instruction.get_output()).groups()

                            try:
                                field_analysis = list(self.dx.find_fields(out_sp[0], out_sp[1], out_sp[2]))
                                if field_analysis:
                                    return field_analysis[0]
                                else:
                                    for field in self.dx.get_class_analysis(out_sp[0]).get_vm_class().get_fields():
                                        if field.get_name() == out_sp[1] and field.get_descriptor() == out_sp[2]:
                                            return FieldClassAnalysis(field)
                            except Exception:
                                return None
        return None

    def find_text_fields(self):
        try:
            # Get all the input fields from the xml layout files.

            input_fields = {}
            for xml_layout_file in filter(lambda x: x.startswith('res/layout'), self.apk.get_files()):
                try:
                    input_fields.update(self.get_input_fields_with_input_types_from_xml(xml_layout_file))
                except Exception:
                    pass

            # Combine all information into a TextField dict.
            text_fields = {}

            for field_id in input_fields:
                text_fields[field_id] = TextField(field_id, self.field_refs[field_id].get_name(),
                                                  input_fields[field_id]['type'], self.field_refs[field_id],
                                                  is_password=input_fields[field_id]['is_password'])

            self.smart_inputs['all'] = list(text_fields.values())

            # Group input fields by activity (if possible).

            for activity_name in self.apk.get_activities():
                self.logger.debug('Analyzing activity {0}'.format(activity_name))

                if activity_name in self.classes_dict:
                    # Include also the internal classes of the activity.
                    class_objects = [self.classes_dict[dot_class_name] for dot_class_name in self.classes_dict
                                     if dot_class_name == activity_name or
                                     dot_class_name.startswith('{0}$'.format(activity_name))]

                    input_types_for_fields = {}
                    for class_object in class_objects:
                        # Find all XML layouts referenced in setContentView in activity bytecode.
                        activity_xml_file = self.get_activity_xml(class_object)

                        if not activity_xml_file:
                            continue

                        try:
                            input_types_for_fields.update(
                                self.get_input_fields_with_input_types_from_xml(activity_xml_file))
                        except Exception:
                            pass

                    if not input_types_for_fields:
                        self.logger.debug('No XMLs found for activity {0}'.format(activity_name))
                        continue

                    # Combine all information into a TextField dict.
                    text_fields = {}

                    for field_id in input_types_for_fields:
                        for class_object in class_objects:
                            field = self.get_input_field_from_code(class_object, field_id)

                            if field:
                                tf = TextField(field_id, self.field_refs[field_id].get_name(),
                                               input_types_for_fields[field_id]['type'], self.field_refs[field_id],
                                               field, is_password=input_types_for_fields[field_id]['is_password'])
                                text_fields[field_id] = tf
                            else:
                                tf = TextField(field_id, self.field_refs[field_id].get_name(),
                                               input_types_for_fields[field_id]['type'], self.field_refs[field_id],
                                               is_password=input_types_for_fields[field_id]['is_password'])
                                if field_id not in text_fields:
                                    text_fields[field_id] = tf

                    if not text_fields:
                        self.logger.debug('No text fields found for activity {0}'.format(activity_name))
                    else:
                        self.smart_inputs[activity_name] = list(text_fields.values())

        except Exception as e:
            self.logger.warning('There was a problem during the search for text fields: {0}'.format(e))

        finally:
            if len(self.smart_inputs) > 0:
                self.logger.debug('{0} text fields identified'.format(len(self.smart_inputs)))

        return self.smart_inputs

    def get_smart_input_for_id(self, input_id: str):
        # No id was provided, return the default text.
        if not input_id:
            return self.default

        to_return = None
        item = None
        if 'all' in self.smart_inputs:
            for item in self.smart_inputs['all']:
                if item.name == input_id:
                    if item.type_variation in self.type_variation:
                        to_return = self.type_variation[item.type_variation]
                        break
                    if item.type_class in self.type_class:
                        to_return = self.type_class[item.type_class]
                        break
        if to_return and item:
            # This field requires a specific input.
            self.logger.info('Possible input for Editable({0}): "{1}"'.format(item, to_return))
        elif 'username' in input_id.lower() or 'email' in input_id.lower() or 'user' in input_id.lower():
            # Maybe this is a username field.
            to_return = self.type_variation['TYPE_TEXT_VARIATION_EMAIL_ADDRESS']
            self.logger.info('Using username input for Editable(id={0}): "{1}"'.format(input_id, to_return))
        elif 'password' in input_id.lower() or 'pwd' in input_id.lower() or 'secret' in input_id.lower():
            # Maybe this is a password field.
            to_return = self.type_variation['TYPE_TEXT_VARIATION_PASSWORD']
            self.logger.info('Using password input for Editable(id={0}): "{1}"'.format(input_id, to_return))
        else:
            # No hint for this field, using the default text.
            to_return = self.default
            self.logger.info('Using default input for Editable(id={0}): "{1}"'.format(input_id, to_return))
        return to_return
