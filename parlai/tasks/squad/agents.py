# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from parlai.core.teachers import FixedDialogTeacher, DialogTeacher, ParlAIDialogTeacher
from .build import build

import copy
import json
import os


class IndexTeacher(FixedDialogTeacher):
    """Hand-written SQuAD teacher, which loads the json squad data and
    implements its own `act()` method for interacting with student agent,
    rather than inheriting from the core Dialog Teacher. This code is here as
    an example of rolling your own without inheritance.

    This teacher also provides access to the "answer_start" indices that
    specify the location of the answer in the context.
    """

    def __init__(self, opt, shared=None):
        build(opt)
        super().__init__(opt, shared)

        if self.datatype.startswith('train'):
            suffix = 'train'
        else:
            suffix = 'dev'
        datapath = os.path.join(
            opt['datapath'],
            'SQuAD',
            suffix + '-v1.1.json'
        )
        self.data = self._setup_data(datapath)

        self.id = 'squad'
        self.reset()

    def num_examples(self):
        return len(self.examples)

    def num_episodes(self):
        return self.num_examples()

    def get(self, episode_idx, entry_idx=None):
        article_idx, paragraph_idx, qa_idx = self.examples[episode_idx]
        article = self.squad[article_idx]
        paragraph = article['paragraphs'][paragraph_idx]
        qa = paragraph['qas'][qa_idx]
        question = qa['question']
        answers = []
        answer_starts = []
        for a in qa['answers']:
            answers.append(a['text'])
            answer_starts.append(a['answer_start'])
        context = paragraph['context']

        action = {
            'id': 'squad',
            'text': context + '\n' + question,
            'labels': answers,
            'episode_done': True,
            'answer_starts': answer_starts
        }
        return action

    def _setup_data(self, path):
        with open(path) as data_file:
            self.squad = json.load(data_file)['data']
        self.examples = []

        for article_idx in range(len(self.squad)):
            article = self.squad[article_idx]
            for paragraph_idx in range(len(article['paragraphs'])):
                paragraph = article['paragraphs'][paragraph_idx]
                num_questions = len(paragraph['qas'])
                for qa_idx in range(num_questions):
                    self.examples.append((article_idx, paragraph_idx, qa_idx))


class DefaultTeacher(DialogTeacher):
    """This version of SQuAD inherits from the core Dialog Teacher, which just
    requires it to define an iterator over its data `setup_data` in order to
    inherit basic metrics, a default `act` function.
    For SQuAD, this does not efficiently store the paragraphs in memory.
    """

    def __init__(self, opt, shared=None):
        self.datatype = opt['datatype']
        build(opt)
        if opt['datatype'].startswith('train'):
            suffix = 'train'
        else:
            suffix = 'dev'
        opt['datafile'] = os.path.join(opt['datapath'], 'SQuAD',
                                       suffix + '-v1.1.json')
        self.id = 'squad'
        super().__init__(opt, shared)

    def setup_data(self, path):
        print('loading: ' + path)
        with open(path) as data_file:
            self.squad = json.load(data_file)['data']
        for article in self.squad:
            # each paragraph is a context for the attached questions
            for paragraph in article['paragraphs']:
                # each question is an example
                for qa in paragraph['qas']:
                    question = qa['question']
                    answers = (a['text'] for a in qa['answers'])
                    context = paragraph['context']
                    yield (context + '\n' + question, answers), True


class OpenSquadTeacher(DialogTeacher):
    """This version of SQuAD inherits from the core Dialog Teacher, which just
    requires it to define an iterator over its data `setup_data` in order to
    inherit basic metrics, a default `act` function.
    Note: This teacher omits the context paragraph
    """

    def __init__(self, opt, shared=None):
        self.datatype = opt['datatype']
        build(opt)
        if opt['datatype'].startswith('train'):
            suffix = 'train'
        else:
            suffix = 'dev'
        opt['datafile'] = os.path.join(opt['datapath'], 'SQuAD',
                                       suffix + '-v1.1.json')
        self.id = 'squad'
        super().__init__(opt, shared)

    def setup_data(self, path):
        print('loading: ' + path)
        with open(path) as data_file:
            self.squad = json.load(data_file)['data']
        for article in self.squad:
            # each paragraph is a context for the attached questions
            for paragraph in article['paragraphs']:
                # each question is an example
                for qa in paragraph['qas']:
                    question = qa['question']
                    answers = (a['text'] for a in qa['answers'])
                    yield (question, answers), True


class TitleTeacher(DefaultTeacher):
    """This version of SquAD inherits from the Default Teacher. The only
    difference is that the 'text' field of an observation will contain
    the title of the article separated by a newline from the paragraph and the
    query.
    Note: The title will contain underscores, as it is the part of the link for
    the Wikipedia page; i.e., the article is at the site:
    https://en.wikipedia.org/wiki/{TITLE}
    Depending on your task, you may wish to remove underscores.
    """

    def __init__(self, opt, shared=None):
        self.id = 'squad_title'
        build(opt)
        super().__init__(opt, shared)

    def setup_data(self, path):
        print('loading: ' + path)
        with open(path) as data_file:
            self.squad = json.load(data_file)['data']
        for article in self.squad:
            title = article['title']
            # each paragraph is a context for the attached questions
            for paragraph in article['paragraphs']:
                # each question is an example
                for qa in paragraph['qas']:
                    question = qa['question']
                    answers = (a['text'] for a in qa['answers'])
                    context = paragraph['context']
                    yield (
                        '\n'.join([title, context, question]),
                        answers
                    ), True


class FulldocTeacher(ParlAIDialogTeacher):
    def __init__(self, opt, shared=None):
        build(opt)
        opt = copy.deepcopy(opt)
        if opt['datatype'].startswith('train'):
            suffix = 'train'
        else:
            suffix = 'valid'
        datafile = os.path.join(opt['datapath'],
                                'SQuAD-fulldoc',
                                "squad_fulldocs." + suffix + ":ordered")
        opt['parlaidialogteacher_datafile'] = datafile
        super().__init__(opt, shared)
        self.id = 'squad-fulldoc'
        self.reset()


class SentenceTeacher(DefaultTeacher):
    """This version of SquAD inherits from the Default Teacher. The label
    field of an observation will contain the sentence that contains the
    answer instead of the actual answer.
    """

    def __init__(self, opt, shared=None):
        self.id = 'squad_title'
        build(opt)
        try:
            import nltk
        except ImportError:
            raise ImportError('Please install nltk (e.g. pip install nltk).')
        # nltk-specific setup
        st_path = 'tokenizers/punkt/{0}.pickle'.format('english')
        try:
            self.sent_tok = nltk.data.load(st_path)
        except LookupError:
            nltk.download('punkt')
            self.sent_tok = nltk.data.load(st_path)
        super().__init__(opt, shared)

    def setup_data(self, path):
        print('loading: ' + path)
        with open(path) as data_file:
            self.squad = json.load(data_file)['data']
        for article in self.squad:
            # each paragraph is a context for the attached questions
            for paragraph in article['paragraphs']:
                # each question is an example
                for qa in paragraph['qas']:
                    question = qa['question']
                    answers = [a['text'] for a in qa['answers']]
                    context = paragraph['context']
                    # temporarily remove '.', '?', '!' from answers for proper
                    # sentence tokenization
                    edited_answers = []
                    for answer in answers:
                        new_answer = answer.replace(
                            '.', '').replace('?', '').replace('!', '')
                        context = context.replace(answer, new_answer)
                        edited_answers.append(new_answer)

                    edited_sentences = self.sent_tok.tokenize(context)
                    sentences = []

                    for sentence in edited_sentences:
                        for i in range(len(edited_answers)):
                            sentence = sentence.replace(edited_answers[i],
                                                        answers[i])
                            sentences.append(sentence)

                    for i in range(len(edited_answers)):
                        context = context.replace(edited_answers[i],
                                                  answers[i])

                    labels = []
                    for sentence in sentences:
                        for answer in answers:
                            if answer in sentence and sentence not in labels:
                                labels.append(sentence)
                                break
                    yield (
                        '\n'.join([context, question]),
                        (label for label in labels)
                    ), True


class SentenceIndexTeacher(IndexTeacher):
    """Index teacher with the sentences that contain the answers as the labels.
    """

    def __init__(self, opt, shared=None):
        super().__init__(opt, shared)

        try:
            import nltk
        except ImportError:
            raise ImportError('Please install nltk (e.g. pip install nltk).')
        # nltk-specific setup
        st_path = 'tokenizers/punkt/{0}.pickle'.format('english')
        try:
            self.sent_tok = nltk.data.load(st_path)
        except LookupError:
            nltk.download('punkt')
            self.sent_tok = nltk.data.load(st_path)

    def get(self, episode_idx, entry_idx=None):
        article_idx, paragraph_idx, qa_idx = self.examples[episode_idx]
        article = self.squad[article_idx]
        paragraph = article['paragraphs'][paragraph_idx]
        qa = paragraph['qas'][qa_idx]
        context = paragraph['context']
        question = qa['question']

        answers = [a['text'] for a in qa['answers']]

        # temporarily remove '.', '?', '!' from answers for proper sentence
        # tokenization
        edited_answers = []
        for answer in answers:
            new_answer = answer.replace(
                '.', '').replace('?', '').replace('!', '')
            context = context.replace(answer, new_answer)
            edited_answers.append(new_answer)

        edited_sentences = self.sent_tok.tokenize(context)
        sentences = []

        for sentence in edited_sentences:
            for i in range(len(edited_answers)):
                sentence = sentence.replace(edited_answers[i], answers[i])
                sentences.append(sentence)

        for i in range(len(edited_answers)):
            context = context.replace(edited_answers[i], answers[i])

        labels = []
        label_starts = []
        for sentence in sentences:
            for answer in answers:
                if answer in sentence and sentence not in labels:
                    labels.append(sentence)
                    label_starts.append(context.index(sentence))
                    break

        action = {
            'id': 'squad',
            'text': context + '\n' + question,
            'labels': labels,
            'episode_done': True,
            'answer_starts': label_starts
        }
        return action
