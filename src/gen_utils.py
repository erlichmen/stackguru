def tag_to_key_name(tag):
    return tag.replace("*", "__WC__")

def key_name_to_tag(tag):
    return tag.replace("__WC__", "*")
