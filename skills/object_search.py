"""
Object Search Skill
"""

from vision.object_search import searcher


def search_object(name):

    found = searcher.find(name)

    if found:

        return f"I found the {name}."

    return f"I couldn't find the {name}."