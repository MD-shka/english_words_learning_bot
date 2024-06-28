import os
import logging
import json
import wordfreq
import asyncio
import aiohttp
import deepl
import nltk
from nltk.corpus import (
    stopwords,
    wordnet as wn,
    words as nltk_words
)
from dotenv import load_dotenv


load_dotenv()


DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

nltk.download([
    'punkt',
    'stopwords',
    'wordnet',
    'averaged_perceptron_tagger',
    'words'
])

prepositions = {
    'about', 'above', 'across', 'after', 'against', 'along', 'among', 'around', 'at', 'before', 'behind', 'below',
    'beneath', 'beside', 'between', 'beyond', 'but', 'by', 'concerning', 'despite', 'down', 'during', 'except', 'for',
    'from', 'in', 'inside', 'into', 'like', 'near', 'of', 'off', 'on', 'onto', 'out', 'outside', 'over', 'past',
    'regarding', 'since', 'through', 'to', 'toward', 'under', 'underneath', 'until', 'up', 'upon', 'with', 'within',
    'without'
}

stop_words = set(stopwords.words('english'))


async def is_preposition(word):
    return word.lower() in prepositions


async def is_stop_word(word):
    return word.lower() in stop_words


async def is_valid_word(word):
    return word.lower() in nltk_words.words()


async def is_base_form(word):
    synsets = wn.synsets(word)
    if not synsets:
        return False
    lemma_names = set()
    for synset in synsets:
        lemma_names.update(synset.lemma_names())
    return word in lemma_names


def translate_text(translator, word, target_lang):
    return translator.translate_text(word, target_lang=target_lang)


async def translate_word(word, translator, target_lang='RU'):
    loop = asyncio.get_event_loop()
    translation = await loop.run_in_executor(
        None, translate_text, translator, word, target_lang
    )
    return translation.text


async def estimate_word_difficulty(word):
    freq = wordfreq.word_frequency(word, 'en')
    if freq > 0.00005:
        return 'Easy'  # Легкий уровень
    elif freq > 0.00001:
        return 'Intermediate'  # Средний уровен
    else:
        return 'Advanced'  # Сложный уровень


async def filter_words(input_filename, output_filename, deep_translator):
    with open(input_filename, 'r') as f:
        words_list = [line.strip() for line in f if line.strip()]

    async with aiohttp.ClientSession():
        tasks = []
        valid_words = []
        for i, word in enumerate(words_list):
            if i % 100 == 0:
                logging.info(f'Processing word {i + 1}/{len(words_list)}: {word}')
            if not await is_preposition(word) and not await is_stop_word(word):
                if await is_valid_word(word) and await is_base_form(word):
                    tasks.append(translate_word(word, deep_translator))
                    valid_words.append(word)

        translations = await asyncio.gather(*tasks)

    words_json = []

    for word, translation in zip(valid_words, translations):
        words_json.append({
            'word': word,
            'translation': translation,
            'grade': await estimate_word_difficulty(word)
        })

    with open(output_filename, 'w') as f:
        json.dump(words_json, f, ensure_ascii=False, indent=4)


async def main():
    input_file_path = 'raw_words.txt'
    output_file_path = 'db/dictionary.json'
    deepl_translator = deepl.Translator(DEEPL_API_KEY)
    await filter_words(input_file_path, output_file_path, deepl_translator)
    logging.info('Finished processing.')

if __name__ == '__main__':
    asyncio.run(main())
