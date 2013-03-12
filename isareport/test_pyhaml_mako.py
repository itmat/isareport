import haml
from mako import lookup,template

l = lookup.TemplateLookup(["static/templates"],
    preprocessor = haml.preprocessor
) 

t = l.get_template("hello.haml")

print t.render(name='jack')