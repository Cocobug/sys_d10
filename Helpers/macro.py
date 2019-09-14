#encoding:UTF-8
import sys,os,traceback
import re,argparse,configparser
from os import listdir
from os.path import isfile, join,basename
import subprocess
import blessings
term=blessings.Terminal()

parser = argparse.ArgumentParser(description='Macro generator')
parser.add_argument('command',choices=["macro","god","diff",'show',"index"],help="The selected command")
parser.add_argument('characters',default=["all"],help="Name of the characters to list, all by default",nargs="*")
parser.add_argument("-o",metavar="output",default="tty",help="File for the output command, tty by default",nargs="?")
parser.add_argument("-s",metavar="suffix",default="",help="Suffix to append to all the files",nargs="?")
parser.add_argument("-v",default=False,action='store_true',help="Default")
parser.add_argument("--version",default="@~1",help="The version to pick from or from wich to make the diff from",nargs="?")
verbose=False
def dprint(text):
    if verbose:
        print(text)
reserved_chars=["God.ini"]

errors={
    "notfound":term.red("[Error] Couldn't find {char} in the Character directory"),
    "sectionnotfound":term.red("[Error] Coulnd't find section {section} in {where}"),
    "noreplacement":term.yellow("[Warning] Couldn't find replacement for {var} in {where}")
}
god=configparser.ConfigParser(inline_comment_prefixes="#")
god.read("Characters/God.ini")

def write_index(output,suffix):
    list=[f for f in listdir(output) if (f != "index.html" and isfile(join(output, f)))]
    list.sort() #key=lambda a: a[:6]
    towrite="""<html>
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <link rel="stylesheet" type="text/css" href="../term.css"/>

    </head>

    <body class="f9 b9">
    <pre>
<span class="bold">Liste des fichiers</span>
"""
    for file in list:
        towrite+='    <span class="bold"><a href="./{}">&rsaquo; {}</a></span>\n'.format(file,file[:-5].title())
    towrite+="""    </pre>
    </body>
</html>"""
    if output=="tty":
        print(towrite)
        return
    with open(join(output,"index.html"),"w") as f:
        f.write(towrite)

def save_text_ansi(foutput,ret):
    pi=subprocess.Popen(("./ansi2html.sh","--palette=xterm"),stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    e=str.encode(ret,"utf8")
    pi.stdin.write(e)
    pi.stdin.close()

    with open(foutput,"wb") as f:
        while True:
            line=pi.stdout.readline()
            if not line:
                break
            f.write(line)


def macro(characters,output,version,suffix):
    list_files,names=get_char(characters)
    if not list_files:
        return
    ret=""
    for file,name in zip(list_files,names):
        ret=macro_one(file,output,version,suffix)
        if output=="tty":
            print(ret)
        else:
            foutput=join(output,"{}_macro{}.html".format(name,suffix))
            save_text_ansi(foutput,ret)

def macro_one(character,output,version,suffix):
    config=configparser.ConfigParser(inline_comment_prefixes="#")
    config.read(character)
    ret=term.bold(character)+"\n"
    for sect in config.sections():
        try:
            text=""
            if (config[sect]["macro"] != "" or config[sect]["others"] !="" or config[sect]["self"] !=""):
                text+=term.bold_blue("[{name}]\n".format(name=sect))
                selfw=replace_vars('/w {you} ',config,god,"self",sect,character,godlink=True)
                if (config[sect]["macro"]):
                    text+=replace_vars(config[sect]["macro"],config,god,"macro",sect,character,godlink=True)+"\n"
                if (config[sect]['self']!=""):
                    for l in replace_vars(config[sect]["self"],config,god,"self",sect,character,godlink=True).split("\n"):
                        text+=selfw+l+"\n"
                if (config[sect]["others"]!=""):
                    text+=replace_vars(config[sect]["others"],config,god,"others",sect,character,godlink=True)+"\n"
                ret+=text
        except KeyError as e:
            #if(e=="macro"):
            #    pass # No macro found, not really important
            print(errors["sectionnotfound"].format(section=e,where=sect))

    return ret

def show(characters,output,version,suffix):
    list_files,names=get_char(characters)
    if not list_files:
        return
    ret=""
    for file,name in zip(list_files,names):
        ret=show_one(file,output,version,suffix)
        if output=="tty":
            print(ret)
        else:
            foutput=join(output,"{}{}.html".format(name,suffix))
            save_text_ansi(foutput,ret)

def show_one(character,output,version,suffix):
    config=configparser.ConfigParser(inline_comment_prefixes="#")
    config.read(character)
    ret=""
    for sect in config.sections():
        try:
            if ("display_name" not in config[sect]):
                continue
            text=""
            text+=term.bold_blue("[{level}] {title} [{cost}]\n").format( title=config[sect]["display_name"], level=config[sect]["level"],cost=config[sect]["cost"])
            for dname,sname in (("Type de technique","type"),('Description',"description"),("Description personelle",'self'),("Description publique","others"),("Spécial","special")):
                try:
                    if not config[sect][sname]:
                        continue
                    content=replace_vars(config[sect][sname],config,god,sname,sect,character)
                    adden=" {t}\n   {c}\n".format(t=term.blue_underline(dname),c=content.replace("\n","\n   "))
                    text+=adden
                except KeyError:
                    dprint(errors["sectionnotfound"].format(section=sname,where=sect))
            ret+=text+'\n'
        except KeyError as e:
            print(errors["sectionnotfound"].format(section=e,where=sect))
    return ret

toreplace=re.compile("(?!@)\{([\w_-]+)\}")
def replace_vars(text,char,god,section,name,character,godlink=False):
    vars=toreplace.findall(text)
    if vars:
        for group in vars:
            try:
                text=text.replace("{"+group+"}",char[name][group])
            except:
                try:
                    if character not in god:
                        w="DEFAULT"
                    else:
                        w=character
                    if group[0]=="b" and godlink:
                        if group not in god[w]:
                            raise KeyError
                        link="@{God|"+group+"}"
                    else:
                        link=god[w][group]
                    text=text.replace("{"+group+"}",link)
                except KeyError as e:
                    dprint(errors["noreplacement"].format(var=group,where=name+"@"+character))
    return text

def god_macro(characters,output,version,suffix):
    config=configparser.ConfigParser(inline_comment_prefixes="#")
    config.read(join("Characters","God.ini"))
    ret="!setattr --name God --silent "
    for sect in config.sections():
        for elt in config[sect]:
            if elt in config["DEFAULT"]:
                continue
                print(elt)
            ret+=" --{}|{}".format(elt,config[sect][elt])
    print(ret)

def index(characters,output,version,suffix):
    write_index(output,suffix)

def diff(characters,output,version,suffix):
    import datetime
    chars,names=get_char(characters,all=True)
    if len(chars)==0:
        dprint(errors["notfound"].format(char="any character"))
        return
    list=["git", "diff",version,"--word-diff=color","-U5"]+chars
    if output=="tty":
        dprint("Printing diff")
        pi=subprocess.check_output(list).decode("utf-8")
        print(pi)
    else:
        proc=subprocess.Popen(list,stdout=subprocess.PIPE)
        pi=subprocess.check_output(("./ansi2html.sh"),stdin=proc.stdout)
        date=datetime.datetime.now().strftime("%y%m%d %Hh%M")
        save_file=join(output,"{}{}.html".format(date,suffix))
        with open(save_file,"wb") as file:
            file.write(pi)

def get_char(names,all=False):
    if names[0]=="all":
        return get_all_chars(all=all)
    char,rnames=[],[]
    for n in names:
        c=join("Characters", n+".ini")
        if isfile(c):
            char.append(c)
            rnames.append(n)
        else:
            dprint(errors["notfound"].format(char=c))
    return char,rnames

def get_all_chars(all):
    if all:
        c=[]
    else:
        c=reserved_chars
    names=[f for f in listdir("Characters") if (f not in c and isfile(join("Characters", f)))]
    return [join("Characters", f) for f in names],[n[:-4] for n in names] # MOAR BLOBSHITCODING

if __name__ == '__main__':
    try:
        args=parser.parse_args(sys.argv[1:])
        verbose=args.v
    except:
        parser.print_help()
        sys.exit()
    if args.s!="":
        args.s=" "+args.s
    commands={"macro":macro,"god":god_macro,"diff":diff,"show":show,"index":index}
    commands[args.command](args.characters,args.o,args.version,args.s)
