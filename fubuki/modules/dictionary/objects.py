from functools import cached_property


class Definition:
    def __init__(self, definition_data):
        self._data = definition_data
        self.definition = self._data.pop("definition")
        self.example = self._data.pop("example", None)
        self.synonyms = self._data.pop("synonyms", None)

    def __repr__(self):
        return "<{0.__class__.__name__} definition={0.definition!r}>".format(self)

class Meaning:
    def __init__(self, meaning_data):
        self._data = meaning_data
        self.part_of_speech = self._data.pop("partOfSpeech")

    @cached_property
    def definitions(self):
        return [*map(Definition, self._data.pop("definitions"))]

    def __repr__(self):
        return "<{0.__class__.__name__} part_of_speech={0.part_of_speech!r} definitions={1}>".format(self, len(self.definitions))

class Word:
    def __init__(self, word_data):
        self._data = word_data
        self.word = self._data.pop("word")
        self.phonetics = self._data.pop("phonetics")

    @cached_property
    def meanings(self):
        return [*map(Meaning, self._data.pop("meanings"))]

    def __repr__(self):
        return "<{0.__class__.__name__} word={0.word!r} meanings={1}>".format(self, len(self.meanings))

class DictionaryResponse:
    def __init__(self, response_data):
        self._data = response_data

    @cached_property
    def words(self):
        return [*map(Word, self._data)]
