#! python3
# -*- encoding: utf-8 -*-
'''
Current module: rtsf.p_yaml_cases

Rough version history:
v1.0    Original version to use

********************************************************************
    @AUTHOR:  Administrator-Bruce Luo(罗科峰)
    MAIL:    lkf20031988@163.com
    RCS:      rtsf.p_testcase,v 1.0 2018年7月14日
    FROM:   2018年7月14日
********************************************************************

======================================================================

UI and Web Http automation frame for python.

'''
import yaml
import json
import os,re,io,ast
from rtsf.p_applog import logger
from rtsf import p_exception,p_compat
from rtsf.p_common import FileSystemUtils,CommonUtils,ModuleUtils
from rtsf.p_compat import numeric_types


variable_regexp = r"\$([\w_]+)"
function_regexp = r"\$\{([\w_]+\([\$\w\.\-_ =,]*\))\}"
function_regexp_compile = re.compile(r"^([\w_]+)\(([\$\w\.\-_ =,]*)\)$")

def extract_variables(content):
    """ extract all variable names from content, which is in format $variable
    @param (str) content
    @return (list) variable name list

    e.g. 
    print(extract_variables("abc")); # => []
    print(extract_variables("$variable")); # => ["variable"]
    print(extract_variables("http://$url")); # => ['url']
    print(extract_variables("/blog/$postid")); # => ["postid"]
    print(extract_variables("/$var1/$var2")); # => ["var1", "var2"]
    
    """
    try:
        return re.findall(variable_regexp, content)
    except TypeError:
        return []

def extract_functions(content):
    """ extract all functions from string content, which are in format ${fun()}
    @param (str) content
    @return (list) functions list

    e.g. 
    print(extract_functions('${func(5)}')); # => ["func(5)"]
    print(extract_functions('${func(a=1, b=2)}')); # => ["func(a=1, b=2)"]
    print(extract_functions('${func(a,b,c)}')); # => ['func(a,b,c)']
    print(extract_functions('/api/1000?_t=${get_timestamp()}')); # => ["get_timestamp()"]
    print(extract_functions('/api/${add(1, 2)}')); # => ["add(1, 2)"]
    print(extract_functions("/api/${add(1, 2)}?_t=${get_timestamp()}")); # => ["add(1, 2)", "get_timestamp()"]
    """
    try:
        return re.findall(function_regexp, content)
    except TypeError:
        return []

def parse_string_value(str_value):
    """ parse string to number if possible
    e.g. "123" => 123
         "12.2" => 12.3
         "abc" => "abc"
         "$var" => "$var"
    """
    try:
        return ast.literal_eval(str_value)
    except ValueError:
        return str_value
    except SyntaxError:
        # e.g. $var, ${func}
        return str_value

def parse_function(content):
    """ parse function name and args from string content.
    @param (str) content
    @return (dict) function name and args

    e.g. 
    print(parse_function("func()")); # => {'kwargs': {}, 'args': [], 'func_name': 'func'}
    print(parse_function("func(5)")); # => {'kwargs': {}, 'args': [5], 'func_name': 'func'}
    print(parse_function("func(a=1, b=2)")); # => {'kwargs': {'a': 1, 'b': 2}, 'args': [], 'func_name': 'func'}
    print(parse_function('func(a,b,c)')); # => {'kwargs': {}, 'args': ['a', 'b', 'c'], 'func_name': 'func'}
    """
    matched = function_regexp_compile.match(content)
    if not matched:
        raise p_exception.FunctionNotFound("{} not found!".format(content))

    function_meta = {
        "func_name": matched.group(1),
        "args": [],
        "kwargs": {}
    }

    args_str = matched.group(2).replace(" ", "")
    if args_str == "":
        return function_meta

    args_list = args_str.split(',')
    for arg in args_list:
        if '=' in arg:
            key, value = arg.split('=')
            function_meta["kwargs"][key] = parse_string_value(value)
        else:
            function_meta["args"].append(parse_string_value(arg))

    return function_meta

def substitute_variables_with_mapping(content, mapping):
    """ substitute variables in content with mapping
    e.g.
    @params
        content = {
            'request': {
                'url': '/api/users/$uid',
                'headers': {'token': '$token'}
            }
        }
        mapping = {"$uid": 1000}
    @return
        {
            'request': {
                'url': '/api/users/1000',
                'headers': {'token': '$token'}
            }
        }
    """
    if isinstance(content, bool):
        return content

    if isinstance(content, (numeric_types, type)):
        return content

    if not content:
        return content

    if isinstance(content, (list, set, tuple)):
        return [
            substitute_variables_with_mapping(item, mapping)
            for item in content
        ]

    if isinstance(content, dict):
        substituted_data = {}
        for key, value in content.items():
            eval_key = substitute_variables_with_mapping(key, mapping)
            eval_value = substitute_variables_with_mapping(value, mapping)
            substituted_data[eval_key] = eval_value

        return substituted_data

    # content is in string format here
    for var, value in mapping.items():
        if content == var:
            # content is a variable
            content = value
        else:
            content = content.replace(var, str(value))

    return content

class TestCaseParser(object):
#     def __init__(self, action_class_name, preference_action_file):        
#         self._functions, self._variables = {}, {}
#         self.file_path = preference_action_file
#         _Actions = ModuleUtils.get_imported_module(action_class_name)                    
#         self.bind_functions(ModuleUtils.get_callable_class_method_names(_Actions.WebHttp))
#         self._variables = _Actions.WebHttp.glob
    
    def __init__(self, variables={}, functions={}, file_path=None):
        self._functions, self._variables = {}, {}
        self.update_binded_variables(variables)
        self.bind_functions(functions)
        self.file_path = file_path
                        
    def update_binded_variables(self, variables):
        """ bind variables to current testcase parser
        @param variable -> dict
            e.g.
            {"ip": "127.0.0.1"}
        """
        self._variables = variables

    def bind_functions(self, functions):
        """ bind functions to current testcase parser
        @param functions -> dict
            e.g.
            {"test": <function test at 0x03508B30>}
        """
        self._functions = functions
        
    def get_bind_variable(self, variable_name):
        '''
        @return: the value of variable_name
        '''
        return self._get_bind_item("variable", variable_name)
    
    
    def get_bind_function(self, func_name):
        '''
        @param func_name: function name
        @return: object of func_name
        '''
        return self._get_bind_item("function", func_name)
        
    def _get_bind_item(self, item_type, item_name):        
        
        if item_type == "function":            
            if item_name in self._functions:
                return self._functions[item_name]
            else:
                # is not keyword function, continue to search
                pass
        elif item_type == "variable":
            if item_name in self._variables:
                return self._variables[item_name]
        else:
            raise p_exception.ParamsError("bind item should only be function or variable.")

        try:
            # preference functions            
            assert self.file_path is not None
            return ModuleUtils.search_conf_item(self.file_path, item_type, item_name)
        except (AssertionError, p_exception.FunctionNotFound):
            raise p_exception.ParamsError(
                "{} is not defined in bind {}s!".format(item_name, item_type))
             
    def eval_content_with_bind_actions(self, content):
        """ parse content recursively, each variable and function in content will be evaluated.

        @param content =>  any data structure with ${func} or $variable
            
        """
        if content is None:
            return None

        if isinstance(content, (list, tuple)):
            return [self.eval_content_with_bind_actions(item) for item in content]

        if isinstance(content, dict):
            evaluated_data = {}
            for key, value in content.items():
                eval_key = self.eval_content_with_bind_actions(key)
                eval_value = self.eval_content_with_bind_actions(value)
                evaluated_data[eval_key] = eval_value

            return evaluated_data

        if isinstance(content, p_compat.basestring):

            # content is in string format here
            content = content.strip()

            # replace functions with evaluated value
            # Notice: _eval_content_functions must be called before _eval_content_variables
            content = self._eval_content_functions(content)

            # replace variables with binding value
            content = self._eval_content_variables(content)
        
        return content
    
    def _eval_content_functions(self, content):
        functions_list = extract_functions(content)
        for func_content in functions_list:
            function_meta = parse_function(func_content)
            func_name = function_meta['func_name']
            
            args = function_meta.get('args', [])
            kwargs = function_meta.get('kwargs', {})            
            args = self.eval_content_with_bind_actions(args)
            kwargs = self.eval_content_with_bind_actions(kwargs)

            func = self.get_bind_function(func_name)
            eval_value = func(*args, **kwargs)

            func_content = "${" + func_content + "}"
            if func_content == content:
                
                logger.log_debug("eval functions result: {} -> {}".format(func_content, eval_value))
                
                # content is a variable
                content = eval_value
            else:
                tmp = content
                
                # content contains one or many variables
                content = content.replace(
                    func_content,
                    p_compat.str(eval_value), 1
                )
                
                logger.log_debug("eval functions result: {} -> {}".format(tmp, content))
        
        return content
    
    def _eval_content_variables(self, content):
        variables_list = extract_variables(content)
        
        for variable_name in variables_list:
            variable_value = self.get_bind_variable(variable_name)
                        
            if "${}".format(variable_name) == content:
                logger.log_debug("eval variables result: ${} -> {}".format(variable_name, variable_value))
                # content is a variable                
                content = variable_value
            else:
                tmp = content
                                
                # content contains one or several variables
                content = content.replace("${}".format(variable_name),p_compat.str(variable_value), 1)
                
                logger.log_debug("eval variables result: {} -> {}".format(tmp, content))
                
        return content
    
class Yaml(object):

    @staticmethod
    def _check_format(file_path, content):
        """ check testcase format if valid
        """
        if not content:
            # testcase file content is empty
            err_msg = u"Testcase file content is empty: {}".format(file_path)
            logger.log_error(err_msg)
            raise p_exception.FileFormatError(err_msg)

        elif not isinstance(content, (list, dict)):
            # testcase file content does not match testcase format
            err_msg = u"Testcase file content format invalid: {}".format(file_path)
            logger.log_error(err_msg)
            raise p_exception.FileFormatError(err_msg)

    @staticmethod
    def _load_yaml_file(yaml_file):
        """ load yaml file and check file content format
        """
        with io.open(yaml_file, 'r', encoding='utf-8') as stream:
            yaml_content = yaml.load(stream)
            Yaml._check_format(yaml_file, yaml_content)
            return yaml_content

    @staticmethod
    def _load_json_file(json_file):
        """ load json file and check file content format
        """
        with io.open(json_file, encoding='utf-8') as data_file:
            try:
                json_content = json.load(data_file)
            except p_exception.JSONDecodeError:
                err_msg = u"JSONDecodeError: JSON file format error: {}".format(json_file)
                logger.log_error(err_msg)
                raise p_exception.FileFormatError(err_msg)

            Yaml._check_format(json_file, json_content)
            return json_content
        
    @staticmethod
    def load_file(file_path):
        if not os.path.isfile(file_path):
            raise p_exception.FileNotFoundError("{} does not exist.".format(file_path))

        file_suffix = os.path.splitext(file_path)[1].lower()
        if file_suffix == '.json':
            return Yaml._load_json_file(file_path)
        elif file_suffix in ['.yaml', '.yml']:
            return Yaml._load_yaml_file(file_path)
        else:
            # '' or other suffix
            err_msg = u"Unsupported file format: {}".format(file_path)
            logger.log_warning(err_msg)
            return []

    @staticmethod
    def load_folder_files(folder_path, recursive=True):
        """ load folder path, return all files in list format.
        @param
            folder_path: specified folder path to load
            recursive: if True, will load files recursively
        @return: 
             all yaml files or json files with relative path in list format 
        """
        if isinstance(folder_path, (list, set)):
            files = []
            for path in set(folder_path):
                files.extend(Yaml.load_folder_files(path, recursive))

            return files

        if not os.path.exists(folder_path):
            return []

        file_list = []

        for dirpath, dirnames, filenames in os.walk(folder_path):
            filenames_list = []

            for filename in filenames:
                if not filename.endswith(('.yml', '.yaml', '.json')):
                    continue

                filenames_list.append(filename)

            for filename in filenames_list:
                file_path = os.path.join(dirpath, filename)
                file_list.append(file_path)

            if not recursive:
                break
            
        return file_list

class YamlCaseLoader(object):
    overall_def_dict = {
        "api": {},
        "suite": {}
    }
    testcases_cache_mapping = {}
             
    def translate(self):
        ''' usage:
            m = YamlCaseLoader(r"D:\auto\buffer\test.yaml")
            for i in m.translate():print(i)
        :return iterator (case_name, execute_function)
        '''
        if not self.check():
            return 
        
        for idx in range(len(self.testcases)):
            testing = self.testcases[idx]
            case_id = testing.get("testcaseid")
            case_name = FileSystemUtils.get_legal_filename("%s[%s]" %(case_id,p_compat.str(testing[self.__case_title_field])))
                         
            # executer actions
            execute_actionss = []
            for field in self.__executer_seq_fields:
                steps_info = testing.get(field)                                
                for execute_function in steps_info:
                    if not execute_function:
                        continue
                    execute_actionss.append(execute_function)                
            yield (case_name, execute_actionss, idx)
    
    def check(self):
        ''' usage:
            print(YamlModel(r"D:\auto\buffer\test.yaml").check()    )
        :return Ture/False
        '''
        result = True
        self.testcases,invalid_cases = self.getYamlCasesValue()
        if invalid_cases:
            print("Waring: Yaml need available fields:")
            for k,v in invalid_cases.items():
                print("\t%s -> %r" %(k, v))
            result = False
        elif not self.testcases:
            print('Warning: Invalid Yaml Test Model.')
            result = False
            
        return result
    
    @staticmethod
    def load_dependencies(path_or_yamlfile):
        """ load all api and suite definitions.
        @param path_or_yamlfile:  dir path or yamlfile path where have api folder and suite folder 
        """
        if os.path.isdir(path_or_yamlfile):
            # cases path
            path = os.path.join(os.path.abspath(path_or_yamlfile), "dependencies")
        else:
            # case file path
            path = os.path.join(os.path.dirname(os.path.abspath(path_or_yamlfile)), "dependencies")
            
        api_def_folder = os.path.join(path, "api")
        suite_def_folder = os.path.join(path, "suite")
                
        # load api definitions
        for test_file in Yaml.load_folder_files(api_def_folder):
            YamlCaseLoader.load_api_file(test_file)

        # load suite definitions        
        for suite_file in Yaml.load_folder_files(suite_def_folder):
            suite = YamlCaseLoader.load_file(suite_file)
            if "def" not in suite["project"]:
                raise p_exception.ParamsError("def missed in suite file: {}!".format(suite_file))

            call_func = suite["project"]["def"]
            function_meta = parse_function(call_func)
            suite["function_meta"] = function_meta
            YamlCaseLoader.overall_def_dict["suite"][function_meta["func_name"]] = suite
    
    @staticmethod
    def load_api_file(file_path):
        """ load api definition from file and store in overall_def_dict["api"]
            @param file_path: yaml file path
            @return: store in overall_def_dict["api"]
        """
        api_items = Yaml.load_file(file_path)
        if not isinstance(api_items, list):
            raise p_exception.FileFormatError("API format error: {}".format(file_path))

        for api_item in api_items:
            if not isinstance(api_item, dict) or len(api_item) != 1:
                raise p_exception.FileFormatError("API format error: {}".format(file_path))

            key, api_dict = api_item.popitem()
            if key != "api" or not isinstance(api_dict, dict) or "def" not in api_dict:
                raise p_exception.FileFormatError("API format error: {}".format(file_path))

            api_def = api_dict.pop("def")
            function_meta = parse_function(api_def)
            func_name = function_meta["func_name"]

            if func_name in YamlCaseLoader.overall_def_dict["api"]:
                logger.log_warning("API definition duplicated: {}".format(func_name))

            api_dict["function_meta"] = function_meta
            YamlCaseLoader.overall_def_dict["api"][func_name] = api_dict
                    
    @staticmethod
    def load_file(yaml_file):
        ''' load yaml file
        @param yaml_file: yaml file path
        @return: testset 
        
        '''
        testset = {
            "file_path": yaml_file,
            "project": {},
            "cases": [],
        }
        word_p = "^[\w-]+$"
        
        if not os.path.isfile(yaml_file):        
            raise p_exception.FileNotFoundError("Not found testcase file {}.".format(yaml_file))
        
        try:
            test_cases = Yaml.load_file(yaml_file)
            logger.log_debug("Yaml raw dict: {}".format(test_cases))
            
            for item in test_cases:
                if not isinstance(item, dict) or len(item) != 1:
                    raise p_exception.FileFormatError("Testcase format error: {}".format(yaml_file))
    
                key, test_block = item.popitem()
                if not isinstance(test_block, dict):
                    raise p_exception.FileFormatError("Testcase format error: {}".format(yaml_file))
    
                if key == "project":
                    testset["project"].update(test_block)
                    testset["name"] = test_block.get("module", "Default Test Set")
    
                elif key == "case":
                    case_id = test_block.pop("id","")
                    desc = test_block.pop("desc","")
                    if not case_id:
                        raise p_exception.ModelFormatError("Some cases do not have 'case_id'.")
                    if not re.search(word_p,case_id):
                        raise p_exception.ModelFormatError("Invalid case_id: {}".format(case_id))                    
                    test_block["name"] = FileSystemUtils.get_legal_filename("%s[%s]" %(case_id, desc))
                    
                    if "api" in test_block:
                        ref_call = test_block["api"]
                        def_block = YamlCaseLoader._get_block_by_name(ref_call, "api")
                        YamlCaseLoader._override_block(def_block, test_block)
                        logger.log_debug("merged api block: {}".format(test_block))
                        testset["cases"].append(test_block)
                        
                    elif "suite" in test_block:
                        ref_call = test_block["suite"]
                        block = YamlCaseLoader._get_block_by_name(ref_call, "suite")
                        logger.log_debug("extend suite block: {}".format(block["cases"]))
                        testset["cases"].extend(block["cases"])
                        
                    else:
                        testset["cases"].append(test_block)
    
                else:
                    logger.log_warning("unexpected block key: {}. block key should only be 'project' or 'case'.".format(key))
            
        except:
            logger.log_error(CommonUtils.get_exception_error())
        finally:
            return testset
    
    @staticmethod
    def load_files(path):
        """ load yaml testcases from file path
        @param path: path could be in several type
            - absolute/relative file path
            - absolute/relative folder path
            - list/set container with file(s) and/or folder(s)
        @return testcase sets list, each testset is corresponding to a file
            [
                testset_dict_1,
                testset_dict_2
            ]
        """
        if isinstance(path, (list, set)):
            testsets = []

            for file_path in set(path):
                if "dependencies" in file_path:
                    continue
                testset = YamlCaseLoader.load_files(file_path)
                if not testset:
                    continue
                testsets.extend(testset)

            return testsets

        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)

        if path in YamlCaseLoader.testcases_cache_mapping:
            return YamlCaseLoader.testcases_cache_mapping[path]

        if os.path.isdir(path):
            files_list = Yaml.load_folder_files(path)
            testcases_list = YamlCaseLoader.load_files(files_list)

        elif os.path.isfile(path):
            try:
                testset = YamlCaseLoader.load_file(path)
                
                if testset["cases"]:
                    testcases_list = [testset]
                else:
                    testcases_list = []
            except p_exception.FileFormatError:
                testcases_list = []

        else:
            logger.log_error(u"file not found: {}".format(path))
            testcases_list = []

        YamlCaseLoader.testcases_cache_mapping[path] = testcases_list
        return testcases_list
    
    @staticmethod
    def _get_block_by_name(ref_call, ref_type):
        """ get test content by reference name
        @params:
            ref_call: e.g. api_v1_Account_Login_POST($UserName, $Password)
            ref_type: "api" or "suite"
        """
        function_meta = parse_function(ref_call)
        func_name = function_meta["func_name"]
        call_args = function_meta["args"]
        block = YamlCaseLoader._get_test_definition(func_name, ref_type)
        def_args = block.get("function_meta").get("args", [])

        if len(call_args) != len(def_args):
            raise p_exception.ParamsError("call args mismatch defined args!")

        args_mapping = {}
        for index, item in enumerate(def_args):
            if call_args[index] == item:
                continue

            args_mapping[item] = call_args[index]

        if args_mapping:
            block = substitute_variables_with_mapping(block, args_mapping)

        return block

    @staticmethod
    def _get_test_definition(name, ref_type):
        """ get expected api or suite.
        @params:
            name: api or suite name
            ref_type: "api" or "suite"
        @return
            expected api info if found, otherwise raise ApiNotFound exception
        """
        block = YamlCaseLoader.overall_def_dict.get(ref_type, {}).get(name)

        if not block:
            err_msg = "{} not found!".format(name)
            if ref_type == "api":
                raise p_exception.ApiNotFound(err_msg)
            else:
                # ref_type == "suite"                
                raise p_exception.SuiteNotFound(err_msg)

        return block

    @staticmethod
    def _override_block(def_block, current_block):
        ''' override def_block with current_block '''       
        
        def_pre = def_block.get("pre_command")
        current_pre = current_block.get("pre_command")
        
        def_post = def_block.get("post_command")
        current_post = current_block.get("post_command")
        
        def_verify = def_block.get("verify")
        current_verify = current_block.get("verify")
        
        current_block.update(def_block)        
        # merge pre_command        
        if not def_pre:
            current_block["pre_command"] = current_pre    
        elif not current_pre:
            current_block["pre_command"] = def_pre    
        else:
            current_block["pre_command"] = current_pre.extend(def_pre)        
        # merge post_command        
        if not def_post:
            current_block["post_command"] = current_post    
        elif not current_post:
            current_block["post_command"] = def_post    
        else:
            current_block["post_command"] = current_post.extend(def_post)
        # merge verify        
        if not def_verify:
            current_block["verify"] = current_verify    
        elif not current_verify:
            current_block["verify"] = def_verify    
        else:
            current_block["verify"] = current_verify.extend(def_verify)
            
        
        
def is_testset(data_structure):
    """ check if data_structure is a testset
    testset should always be in the following data structure:
        {
            "name": "desc1",
            "project": {},
            "cases": [testcase11, testcase12]
        }
    """
    if not isinstance(data_structure, dict):
        return False

    if "name" not in data_structure or "cases" not in data_structure:
        return False

    if not isinstance(data_structure["cases"], list):
        return False

    return True

def is_testsets(data_structure):
    """ check if data_structure is testset or testsets
    testsets should always be in the following data structure:
        testset_dict
        or
        [
            testset_dict_1,
            testset_dict_2
        ]
    """
    if not isinstance(data_structure, list):
        return is_testset(data_structure)

    for item in data_structure:
        if not is_testset(item):
            return False

    return True



