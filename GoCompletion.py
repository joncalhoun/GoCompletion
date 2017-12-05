import json
import sublime
import sublime_plugin
import subprocess

# This is heavily documented as it is my first ST3 plugin. As a result it
# *might* be a useful learning tool for others, but my python skills are shit.

# TODO: Add this to README for removing unwanted completion snippets
"""
# Sublime Text 3 languages list:
ls -1 /Applications/Sublime\ Text.app/Contents/MacOS/Packages/

# Remove all default Sublime Text 3 snippets for Go language
mkdir -p ~/Library/Application\ Support/Sublime\ Text\ 3/Packages/Go/
unzip -l /Applications/Sublime\ Text.app/Contents/MacOS/Packages/Go.sublime-package | grep '.sublime-snippet' | awk '{print $4 " " $5}' | while read f; do touch ~/Library/Application\ Support/Sublime\ Text\ 3/Packages/Go/$f; done
"""


class GoCompletionUpdateCommand(sublime_plugin.TextCommand):
    """Command that can be run via the command pallete.
    """
    def run(self, edit):
        update_plugin()

def update_plugin():
    """Attempts to check that Go is installed by calling `go version` and then installs any third party packages used by this plugin.

    NOTE: This MUST be run before you use this plugin otherwise it will likely not work. I'll eventually fix that, but this works for now.
    """
    try:
        out = must_cmd(["go", "version"])
        print("Using %s" % out)
        must_cmd(["go", "get", "-u", "github.com/nsf/gocode"])
    except CommandError as e:
        sublime.error_message(
            "\n".join([
                "An error occurred while setting GhoST",
                "up. The message is shown below.",
                "",
                e.message
            ])
        )
    except Exception as e:
        sublime.error_message(
            "\n".join([
                "Something wen't wrong. The error msg",
                "is shown below.",
                "",
                str(e)
            ])
        )


class GoCompletion(sublime_plugin.EventListener):
    """The main GoCompletion class that contains all the event listening methods.
    """

    def on_query_completions(self, view, prefix, locations):
        """This is run when the user is typing in the editor and returns possible matching return values. For now it is hardcoded to only work when the syntax is Go.

        See https://www.sublimetext.com/docs/3/api_reference.html#sublime_plugin.EventListener for more info on EventListeners.
        """

        # TODO(joncalhoun): Find a better way to limit syntax
        syntax = view.settings().get('syntax')
        if syntax != "Packages/Go/Go.sublime-syntax":
            return []

        # Autocompletion can be triggered with many cursors, but (AFAIK) it only
        # happens when they all have the same prefix. For simplicty, this only
        # accounts for the first cursor position.
        pos = locations[0]

        # Get all the code from the view. We don't use a file on disk b/c the
        # code may not be saved.
        src = view.substr(sublime.Region(0, view.size()))
        out = must_cmd(["gocode", "-f=json", "autocomplete", str(pos)], src)
        data = json.loads(out)
        if len(data) >= 2:
            ret = build_completions(data[1])
        else:
            ret = []
        return ret

# data should be an array of JSON objects returned by gocode.
def build_completions(data=[]):
    print("data=", data)
    ret = []
    for entry in data:
        if entry["class"] == "func":
            # if entry["package"] == "":
            #     continue
            ret.append(func_completion(entry))
    return ret

def func_completion(entry):
    d = declex(entry["type"])
    return [func_render_text(entry), func_replacement_text(entry)]

def must_cmd(cmd, stdin=None):
    out, err = run_cmd(cmd, stdin)
    if err:
        raise err
    return out

def run_cmd(cmd, stdin=None):
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # out, err = p.communicate()
    if stdin:
        out, err = p.communicate(input=stdin.encode())
    else:
        out, err = p.communicate()
    out = out.decode("utf-8")
    if err:
        msg = "Error while running an external command.\nCommand: %s\nError: %s" % (" ".join(cmd), err.decode("utf-8"))
        return out, CommandError(msg)

    return out, None

def func_render_text(entry):
    params = declex(entry["type"])
    ptypes = []
    for p in params[0]:
        print("p=", p)
        ptypes.append("%s %s" % p)
    ret = "%s(%s)\t%s" % (entry["name"], ", ".join(ptypes), params[1])
    return ret

def func_replacement_text(entry):
    params = declex(entry["type"])
    pnames = []
    for i, p in enumerate(params[0]):
        pnames.append(
            "${%d:%s}" % (i+1, p[0])
        )
    ret = "%s(%s)" % (entry["name"], ", ".join(pnames))
    return ret

# Taken from GoSublime - give credit!!!
def declex(s):
    params = []
    ret = ''
    if s.startswith('func('):
        lp = len(s)
        sp = 5
        ep = sp
        dc = 1
        names = []
        while ep < lp and dc > 0:
            c = s[ep]
            if dc == 1 and c in (',', ')'):
                if sp < ep:
                    n, _, t = s[sp:ep].strip().partition(' ')
                    t = t.strip()
                    if t:
                        for name in names:
                            params.append((name, t))
                        names = []
                        params.append((n, t))
                    else:
                        names.append(n)
                    sp = ep + 1
            if c == '(':
                dc += 1
            elif c == ')':
                dc -= 1
            ep += 1
        ret = s[ep:].strip() if ep < lp else ''
    return (params, ret)
