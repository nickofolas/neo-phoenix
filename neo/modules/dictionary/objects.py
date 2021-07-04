# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
class Definition:
    __slots__ = ("definition", "example", "synonyms")

    def __init__(self, definition_data):
        self.definition = definition_data.pop("definition")
        self.example = definition_data.pop("example", None)
        self.synonyms = definition_data.pop("synonyms", None)

    def __repr__(self):
        return "<{0.__class__.__name__} definition={0.definition!r}>".format(self)


class Meaning:
    __slots__ = ("part_of_speech", "definitions")

    def __init__(self, meaning_data):
        self.part_of_speech = meaning_data.pop("partOfSpeech")
        self.definitions = [*map(Definition, meaning_data.pop("definitions"))]

    def __repr__(self):
        return "<{0.__class__.__name__} part_of_speech={0.part_of_speech!r} definitions={1}>".format(self, len(self.definitions))


class Word:
    __slots__ = ("word", "phonetics", "meanings")

    def __init__(self, word_data):
        self.word = word_data.pop("word")
        self.phonetics = word_data.pop("phonetics")
        self.meanings = [*map(Meaning, word_data.pop("meanings"))]

    def __repr__(self):
        return "<{0.__class__.__name__} word={0.word!r} meanings={1}>".format(self, len(self.meanings))


class DictionaryResponse:
    __slots__ = ("words",)

    def __init__(self, response_data):
        self.words = [*map(Word, response_data)]
