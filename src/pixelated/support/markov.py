#
# Copyright (c) 2015 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

from random import Random

NEW_PARAGRAPH = '\n\n'


class MarkovGenerator(object):

    def __init__(self, texts, random=None, add_paragraph_on_empty_chain=False):
        self._markov_chain = {}
        self._random = random if random else Random()
        self._add_paragraph_on_empty_chain = add_paragraph_on_empty_chain

        for text in filter(lambda _: _ is not None, texts):
            self._extend_chain_with(text)

    def add(self, text):
        self._extend_chain_with(text)

    @staticmethod
    def _triplet_generator(words):
        if len(words) < 3:
            raise ValueError('Expected input with at least three words')

        for i in xrange(len(words) - 2):
            yield ((words[i], words[i + 1]), words[i + 2])

    def _extend_chain_with(self, input_text):
        words = input_text.split()
        gen = self._triplet_generator(words)

        for key, value in gen:
            if key in self._markov_chain:
                self._markov_chain[key].add(value)
            else:
                self._markov_chain[key] = {value}

    def _generate_chain(self, length):
        seed_pair = self._find_good_seed()
        word, next_word = seed_pair
        new_seed = False

        for i in xrange(length):
            yield word

            if new_seed:
                word, next_word = self._find_good_seed()
                if self._add_paragraph_on_empty_chain:
                    yield NEW_PARAGRAPH
                new_seed = False
            else:
                prev_word, word = word, next_word

                try:
                    next_word = self._random_next_word(prev_word, word)
                except KeyError:
                    new_seed = True

    def _random_next_word(self, prev_word, word):
        return self._random.choice(list(self._markov_chain[(prev_word, word)]))

    def _find_good_seed(self):
        max_tries = len(self._markov_chain.keys())
        try_count = 0

        seed_pair = self._random.choice(self._markov_chain.keys())
        while not seed_pair[0][0].isupper() and try_count <= max_tries:
            seed_pair = self._random.choice(self._markov_chain.keys())
            try_count += 1

        if try_count > max_tries:
            raise ValueError('Not able find start word with captial letter')

        return seed_pair

    def generate(self, length):
        if len(self._markov_chain.keys()) == 0:
            raise ValueError('Expected at least three words input')
        return ' '.join(self._generate_chain(length))
