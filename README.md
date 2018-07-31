# rtsf(rock4 test service framework)

**[rock4automation项目](https://github.com/RockFeng0/rock4automation)痛点**
- 集成了 http测试,web UI测试，PC MFC UI测试，PC WPF UI测试，但实际上，QA或者测试人员，可能只需要http相关的api测试，却不得不将整个项目下载安装
- rock4automation项目,打包发布的程序，会将源码封装了exe或者加密为pyd；
- rock4automation项目,打包了相关工具，比如appium-server，java.exe 等等，大量冗余的，非项目源码的工具

**rtsf项目的目标**
- 可扩展，用于打造一个基本的测试服务框架,也许以后可以基于RPC，但是，目前，还只是一个可扩展的模块包
- 精简，拆分业务测试相关的功能、测试框架应有的基础功能、其他工具不再整合，rtsf项目，就是其中的基础功能
- 专注，rtsf已经完成了，自成一体的执行逻辑，测试开发人员，主要精力仅需要投入到，重写和设计测试用例执行过程的run_test函数
- 轻量，少造轮子，多复用标准库和优秀开源项目


## 测试用例模型

> 测试用例模型，计划扩展为, yaml, xml, excel三种，目前已扩展的只有yaml测试用例模型 

### Yaml测试用例模型介绍

- 用例模型，基本保持[rock4automation项目](https://github.com/RockFeng0/rock4automation)的case模型
- 其中的变量和函数的替换，参照了httprunner项目的格式  $VAR ${FUNC}, 该格式取代了我的[rock4automation项目](https://github.com/RockFeng0/rock4automation)中的， #var# 等替换规则
- yaml测试用例，是一个testset(测试集)，可以引入api和suite

> 执行顺序  pre_command(List) -> steps(List) -> post_command(List) -> verify(List)

```
# yaml测试用例，模型示例:
- project:
    name: xxx系统
    module: 登陆模块-功能测试

- case:
    id: ATP-1
    desc: 使用api示例
    
    # 用例分层-使用 api时，必填
    api: test_api()

- case:
    id: ATP-2
    desc: 使用suite示例
    
    # 用例分层-使用 suite时，必填
    suite: test_suite()
    
- case:
    # id 必填
    id: ATP-3
    # desc 必填
    desc: 测试用例-模板格式的设计-模板（全字段）
    
    # responsible 选填
    responsible: rockfeng0
    
    # tester 选填
    tester: rockfeng0
    
    # pre_command 选填
    pre_command:
        - Set(passwd = "123456")
    
    # steps 必填
    steps:
        # request 测试api或者 http /https 时使用
        - request:
            url: https://www.baidu.com
            method: GET
            headers:
            data:
        
        # webdriver 测试web ui 时使用
        - webdriver:
            by: css
            value: "#username"
            index: 0
            timeout: 10
            action: ${sendkey($username)}
        - webdriver:
            action: ${refresh}
        
        # mobiledriver 测试android UI 时使用
        - mobiledriver:
            action: ${refresh}
        
        # wpfdriver 测试pc wpf技术的客户端 ui 时使用    
        - wpfdriver:
            action: 
        
        # mfcdriver 测试pc mfc技术的客户端 ui 时使用    
        - mfcdriver:
            actiion:
    
    # post_command 选填
    post_command:
        - Set(passwd = "123456")
    
    # verify 选填
    verify:
        - VerifyCode("200")
```

模型解释:
- project: name->待测系统的名称; module->测试集名称（一个文件就一个测试集合， 目前，还不支持测试套件的嵌套）
- case: 必填(id->测试用例id; desc->测试用例的描述;steps->测试步骤;verify->校验),选填(responsible->测试责任人;tester->测试执行人;pre_command->测试前置条件(前置钩子);post_command->测试后置条件(后置钩子))
- case-steps: request->http测试; webdriver->web UI测试; mobiledriver->移动端app测试;wpfdriver->使用wpf技术的pc客户端测试;mfcdriver->使用mfc技术的pc客户端测试)

## 测试用例分层

- 测试用例分层，是指在testset的测试集中，添加了api和suite的测试的测试用例.
- 如果，测试用例使用了 api 或者 suite等分层关键字，那么程序会在在指定运行的测试用例同级目录的 dependencies文件夹中寻找api和suite
- api合并，是指测试用例 合并 api用例的键值对。
- suite扩展，是指测试用例 扩展为suite中的用例。

> 注意: 其内在逻辑，其实是，先加载api和suite,以dict形式存储在内置变量中，然后，加载测试集的用例，如果测试用例使用了api则合并，如果测试用例使用了suite则扩展。

### api用例介绍

- api测试用例，实际上是一个最小单元的测试，封装后，便于被suite和testset重复引入
- 应用测试用例的分层思想
- api测试用例中的def的解析，参照了httprunner项目
- 存放路径, 测试用例同级目录下:  dependencies/api/*。yaml, dependencies/api/*。yml, dependencies/api/*。json

```
# api测试用例的示例：
- api:
    # def 必填
    def: test_api()    
    
    # pre_command 选填
    pre_command:
        - Set(passwd = "123456")
    
    # steps 必填
    steps:
        # request 测试api或者 http /https 时使用
        - request:
            url: https://www.baidu.com
            method: GET
            headers:
            data:
        
        # webdriver 测试web ui 时使用
        - webdriver:
            by: css
            value: "#username"
            index: 0
            timeout: 10
            action: ${sendkey($username)}
        - webdriver:
            action: ${refresh}
        
        # mobiledriver 测试android UI 时使用
        - mobiledriver:
            action: ${refresh}
        
        # wpfdriver 测试pc wpf技术的客户端 ui 时使用    
        - wpfdriver:
            action: 
        
        # mfcdriver 测试pc mfc技术的客户端 ui 时使用    
        - mfcdriver:
            actiion:
    
    # post_command 选填
    post_command:
        - Set(passwd = "123456")
    
    # verify 选填
    verify:
        - VerifyCode("200")
```


### suite用例介绍

- suite测试用例，实际上是，由一些api或者一些case，封装后的，相对稳定的，测试用例
- 应用测试用例分层思想，suite也可以被testset引入
- 存放路径, 测试用例同级目录下:  dependencies/suite/*。yaml, dependencies/suite/*。yml, dependencies/suite/*。json

> suite的用例跟 testset差别不大，主要的是，在project中，添加def关键字，定义引入suite的函数入口

```
# suite测试套件的示例：
- project:
    def: test_suite()
            
- case:
    # id 必填
    id: ATP-2
    # desc 必填
    desc: suite测试用例-模板（字段与testset测试用例相同）
    
    # responsible 选填
    responsible: rockfeng0
    
    # tester 选填
    tester: rockfeng0
    
    # pre_command 选填
    pre_command:
        - Set(passwd = "123456")
    
    # steps 必填
    steps:
        # request 测试api或者 http /https 时使用
        - request:
            url: https://www.baidu.com
            method: GET
            headers:
            data:
        
        # webdriver 测试web ui 时使用
        - webdriver:
            by: css
            value: "#username"
            index: 0
            timeout: 10
            action: ${sendkey($username)}
        - webdriver:
            action: ${refresh}
        
        # mobiledriver 测试android UI 时使用
        - mobiledriver:
            action: ${refresh}
        
        # wpfdriver 测试pc wpf技术的客户端 ui 时使用    
        - wpfdriver:
            action: 
        
        # mfcdriver 测试pc mfc技术的客户端 ui 时使用    
        - mfcdriver:
            actiion:
    
    # post_command 选填
    post_command:
        - Set(passwd = "123456")
    
    # verify 选填
    verify:
        - VerifyCode("200")
        
```

## 测试执行方法

> 执行的方法，需要重写，rtsf.p_executer.Runner.run_test函数. 

### 默认情况下，未重写Runner.run_test

> TestRunner()的参数，默认使用Runner实例化对象，

```
# test.py
# coding:utf-8
from rtsf.p_executer import TestRunner,Runner

# 执行测试
runner = TestRunner(runner = Runner)).run(test.yaml')

# 生成测试报告
html_report = runner.gen_html_report()

# 打印测试报告路径
print(html_report)

```

> 测试用例如下：

```
# test.yaml

- project:
    name: rtsf测试框架-测试
    module: 测试执行方法
    
- case:
    id: ATP-1
    desc: 打开百度
    glob_var:
        passwd: 123@Qwe
    glob_regx:
        rex_name: 'id=su value=([\w\-\.\+/=]+)'
    pre_command: 
        - ${SetVar(username, luokefeng)}
        - ${SetVar(password, $passwd)}
    steps:
        - request:
            url: https://www.baidu.com          
            method: GET
    post_command:
        - ${DyStrData(baidu_name,$rex_name)}
    verify:
        - ${VerifyCode(200)}
        - ${VerifyVar(baidu_name, 百度一下)}
        - ${VerifyVar(baidu_name, 123)}

```


### 自定义执行方法，重写Runner.run_test

> 自定义run_test，编写测试用例的执行过程

 注意: 重写的时候，第一个参数，是单个case，不是所有case，**只需要写一个case的执行逻辑**； 重写好 run_test是使用rtsf的主要工作。

```
from rtsf.p_executer import Runner

class DemoRunner(Runner):      
        
    def run_test(self, testcase_dict):
        parser = self.parser
        parser.bind_functions()
        parser.update_binded_variables()
        
        
        tracer = self.tracer
        tracer.start(self.proj_info["module"], testcase_dict["name"], testcase_dict.get("responsible","Administrator"), testcase_dict.get("tester","Administrator"))        
        tracer.section(case_name)
         
        # 还记得，yaml模型介绍的时候，说的执行顺序吗？    pre_command(List) -> steps(List) -> post_command(List) -> verify(List)
        try:            
            tracer.normal("**** precommand")
            precommand = testcase_dict.get("pre_command",[])
            # do something to execute the precommand
            for i in precommand:
                tracer.step("{}".format(i))
             
            self.tracer.normal("**** steps")
            steps = testcase_dict["steps"]
            # do something to execute the steps
            for step in steps:
                # only request or you can control it to webdriver、mobiledriver、mfcdriver、wpfdriver
                if not "request" in step:
                    continue
                 
                url =step["request"]["url"]
                method = step["request"]["method"]                                    
                head = step["request"].get("headers")                 
                data = step["request"].get("data")
                
                self.tracer.step("requests headers -> \n\t{}".format(head))
                self.tracer.step("requests body -> \n\t{}".format(data))
                self.tracer.step("requests:\n\t{} {}".format(method.upper(), url))
                
                # do some thing with requests 
                resp = requests.post(url, data = data, headers = head， ...)
                                
                self.tracer.step("response headers: \n\t{}".format(resp.headers))
                self.tracer.step("response body: \n\t{}".format(resp.text))                                 
            
            self.tracer.normal("**** postcommand")
            postcommand = testcase_dict.get("post_command", [])        
            # do something to execute the postcommand
            for i in postcommand:
                self.tracer.step("{}".format(i))
            
            self.tracer.normal("**** verify")
            verify = testcase_dict.get("verify",[])
            # do something to execute the postcommand
            ...
        except Exception as e:
            tracer.error("something error, %s" %e)
        finally:             
            tracer.stop()
```
> self.parser 解析测试用例的实例，控制全局上下文和映射关键字与执行函数； self.tracer 跟踪执行日志的实例，详细记录每个用例的执行过程，是很关键的；
