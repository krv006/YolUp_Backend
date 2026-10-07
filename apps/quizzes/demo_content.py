"""Mock test (IELTS) ni sinash uchun ORIGINAL demo testlar.

Matnlar va savollar shu loyiha uchun yozilgan (rasmiy IELTS/Cambridge materiallari
EMAS — ular mualliflik huquqi bilan himoyalangan). Maqsad — tizimni sinash:
Reading (2 matn parchasi guruhi), Listening (audio o'rniga matn skripti) va
Writing (2 insho topshirig'i).

Savollar `QuestionWriteSerializer` shaklida (API bilan bir xil) — buyruq ularni
shu serializer orqali tekshiradi.
"""

TITLE_PREFIX = '[DEMO] '


def mcq(text, options, correct):
    return {
        'type': 'single', 'text': text, 'points': 2,
        'options': [{'text': o, 'is_correct': i == correct} for i, o in enumerate(options)],
    }


def tfng(text, answer):
    options = ['True', 'False', 'Not Given']
    return mcq(text, options, options.index(answer))


def blank(text, answers):
    return {'type': 'fill_blank', 'text': text, 'points': 2, 'blanks': [{'answers': answers}]}


def number(text, value):
    return {'type': 'numeric', 'text': text, 'points': 2, 'accepted_answers': [str(value)], 'tolerance': 0}


def essay(text):
    # Insho qo'lda/AI bilan baholanadi — `accepted_answers` faqat shakl talabi uchun
    return {'type': 'text', 'text': text, 'points': 9, 'accepted_answers': ['-']}


def with_group(question, group):
    return {**question, 'group': group}


PASSAGE_BEES = (
    "Over the past two decades, beekeeping has quietly moved from the countryside to the rooftops of "
    "major cities. In London, the number of registered hives rose from about 1,000 in 2008 to more than "
    "6,000 a decade later. Supporters say cities are surprisingly good places for bees. Gardens, parks and "
    "window boxes provide a wide variety of flowers that bloom at different times of the year, while "
    "farmland is often dominated by a single crop that flowers for only a few weeks. Cities also tend to be "
    "a few degrees warmer than the surrounding countryside, and they use far fewer pesticides.\n\n"
    "However, the boom has worried some ecologists. Dr Helen Marsh, who studies pollinators, argues that "
    "honeybees compete with wild bees for the same flowers. In areas with many hives, she found that wild "
    "bumblebees were smaller and produced fewer young. 'Honeybees are managed livestock, not wildlife,' she "
    "says. 'Keeping more of them does not help the species that are really in decline.'\n\n"
    "Beekeepers reply that hives are a gateway to caring about nature. Many urban beekeepers plant "
    "bee-friendly flowers and learn about local ecosystems. Some city councils now run courses and offer "
    "rooftop space to residents. The city of Paris, for example, has promoted hives on public buildings "
    "since 2010, although it has recently begun planting wildflower meadows too, so that wild insects are "
    "not left out.\n\n"
    "Honey from city hives has also attracted attention. Laboratory tests in several cities have found that "
    "it contains no more heavy metals than honey produced in rural areas, which surprised many consumers. "
    "Even so, most urban beekeepers produce only enough honey to share with friends, and few sell it "
    "commercially."
)

PASSAGE_SLEEP = (
    "Most people know that a poor night's sleep makes it hard to concentrate the next day, but researchers "
    "now believe that sleep plays a more active role in learning than was once thought. During the deepest "
    "stages of sleep, the brain appears to replay the events of the day, strengthening some connections "
    "between neurons and letting others fade. This process, known as consolidation, helps to move new "
    "information from short-term storage to long-term memory.\n\n"
    "In one well-known experiment, volunteers were taught a list of word pairs in the evening. Half were "
    "allowed to sleep normally, while the others stayed awake all night. After two days of recovery sleep, "
    "both groups were tested. The group that had slept on the first night remembered about 20 per cent more "
    "pairs, even though both groups had caught up on rest before the test. The researchers concluded that "
    "the first night after learning is especially important.\n\n"
    "Not every kind of memory benefits equally. Sleep seems to help most with facts and with skills such as "
    "playing a piece of music, while it makes less difference for simple tasks that are repeated many "
    "times. Short naps can help too: a nap of 90 minutes, which allows time for a full sleep cycle, "
    "improved performance on a memory test by a similar amount to a full night's sleep, according to one "
    "study, although shorter naps of ten minutes gave smaller benefits.\n\n"
    "Some students respond to exams by studying through the night. Sleep scientists advise against this. "
    "'Cramming feels productive,' says Professor David Okoro, 'but you lose the very process that stores "
    "what you have just learned.' He recommends finishing revision in the early evening and keeping a "
    "regular bedtime in the week before an exam."
)

READING = {
    'title': TITLE_PREFIX + 'IELTS Reading',
    'topic': 'IELTS Reading (demo)',
    'groups': [
        {'title': 'Passage 1 — Bees in the City', 'passage': PASSAGE_BEES},
        {'title': 'Passage 2 — Sleep and Memory', 'passage': PASSAGE_SLEEP},
    ],
    'questions': [
        # Passage 1 — Questions 1-10
        with_group(tfng('There were more than 5,000 additional registered hives in London by 2018 than in 2008.', 'True'), 0),
        with_group(tfng('City temperatures are generally higher than those in the surrounding countryside.', 'True'), 0),
        with_group(tfng('Dr Marsh recommends banning beekeeping in cities.', 'Not Given'), 0),
        with_group(tfng('Paris has stopped supporting hives on public buildings.', 'False'), 0),
        with_group(mcq('What did Dr Marsh find in areas with many hives?', [
            'Wild bumblebees were larger.', 'Wild bumblebees were smaller and produced fewer young.',
            'There were more wild bumblebees.', 'Wild bumblebees were not affected.'], 1), 0),
        with_group(mcq('How do beekeepers respond to the ecologists?', [
            'They say hives help wild insects survive.', 'They deny that honeybees eat wild flowers.',
            'They say hives encourage people to care about nature.', 'They agree to keep fewer hives.'], 2), 0),
        with_group(blank('Cities use far fewer {{1}} than farmland.', ['pesticides']), 0),
        with_group(blank('Some city councils offer {{1}} space to residents.', ['rooftop']), 0),
        with_group(mcq('What did laboratory tests find about honey from city hives?', [
            'It contained more heavy metals than rural honey.', 'It contained no more heavy metals than rural honey.',
            'It was safer than rural honey.', 'It tasted different from rural honey.'], 1), 0),
        with_group(blank("Dr Marsh calls honeybees managed {{1}}, not wildlife.", ['livestock']), 0),
        # Passage 2 — Questions 11-20
        with_group(tfng('Researchers now give sleep a larger role in learning than they once did.', 'True'), 1),
        with_group(tfng('In the word-pair experiment, the volunteers who stayed awake had no recovery sleep before testing.', 'False'), 1),
        with_group(tfng('More than 100 volunteers took part in the word-pair experiment.', 'Not Given'), 1),
        with_group(tfng('A ten-minute nap gave smaller benefits than a ninety-minute nap.', 'True'), 1),
        with_group(mcq('What is the process that moves information into long-term memory called?', [
            'Replay', 'Recovery', 'Consolidation', 'Cramming'], 2), 1),
        with_group(mcq('Sleep helps most with', [
            'simple tasks repeated many times.', 'facts and skills such as playing music.',
            'physical exercise.', 'staying awake at night.'], 1), 1),
        with_group(blank('The group that slept remembered about {{1}} per cent more word pairs.', ['20', 'twenty']), 1),
        with_group(blank('Professor Okoro recommends finishing revision in the early {{1}}.', ['evening']), 1),
        with_group(number('How many minutes long was the nap that allowed a full sleep cycle?', 90), 1),
        with_group(mcq('What does Professor Okoro advise for the week before an exam?', [
            'Study through the night.', 'Keep a regular bedtime.', 'Take ten-minute naps only.',
            'Stop revising.'], 1), 1),
    ],
}

TRANSCRIPT_BOOKING = (
    "Receptionist: Good morning, Greenfield Sports Centre.\n"
    "Caller: Hello, I'd like to book a badminton court for Saturday.\n"
    "Receptionist: Certainly. We have courts free at ten o'clock or at two in the afternoon.\n"
    "Caller: Two would be perfect. It's for four people.\n"
    "Receptionist: A court costs eleven pounds an hour, and rackets can be hired for two pounds each.\n"
    "Caller: We have our own rackets, thanks.\n"
    "Receptionist: May I take a name?\n"
    "Caller: It's Patel — that's P-A-T-E-L.\n"
    "Receptionist: Thank you, Mr Patel. Please arrive ten minutes early to sign in."
)

TRANSCRIPT_LIBRARY = (
    "Welcome to the university library. The ground floor holds newspapers and computers. Silent study is "
    "on the second floor, and group rooms, which must be booked online, are on the third. The library opens "
    "at eight thirty on weekdays and closes at ten at night during exam periods. You can borrow up to twelve "
    "books for four weeks. Overdue books cost fifty pence per day. The café near the entrance is the only "
    "place where food is allowed."
)

LISTENING = {
    'title': TITLE_PREFIX + 'IELTS Listening (matn skripti)',
    'topic': 'IELTS Listening (demo, audio o\'rniga matn)',
    'groups': [
        {'title': 'Part 1 — Booking a court (audio o\'rniga matn)', 'passage': TRANSCRIPT_BOOKING},
        {'title': 'Part 2 — Library tour (audio o\'rniga matn)', 'passage': TRANSCRIPT_LIBRARY},
    ],
    'questions': [
        with_group(blank('The court is booked for {{1}}.', ['Saturday']), 0),
        with_group(mcq('What time is the booking?', ['10 a.m.', '2 p.m.', '4 p.m.'], 1), 0),
        with_group(number('The court costs £___ per hour.', 11), 0),
        with_group(blank("The caller's surname is {{1}}.", ['Patel']), 0),
        with_group(number('Visitors should arrive ___ minutes early.', 10), 0),
        with_group(mcq('On which floor are the group rooms?', ['Ground floor', 'Second floor', 'Third floor'], 2), 1),
        with_group(mcq('How many books can a student borrow?', ['Four', 'Twelve', 'Fifty'], 1), 1),
        with_group(mcq('What is the fine for an overdue book per day?', ['Ten pence', 'Fifty pence', 'One pound'], 1), 1),
        with_group(mcq('Where is food allowed?', ['Silent study area', 'The café', 'Group rooms'], 1), 1),
        with_group(mcq('When does the library close during exam periods?', ['6 p.m.', '8.30 p.m.', '10 p.m.'], 2), 1),
    ],
}

WRITING = {
    'title': TITLE_PREFIX + 'IELTS Writing',
    'topic': 'IELTS Writing (demo)',
    'groups': [],
    'questions': [
        essay(
            "WRITING TASK 1\n\nThe table below shows the percentage of households with internet access "
            "in four countries in 2005 and in 2020.\n\n"
            "Country | 2005 | 2020\nSweden | 76% | 97%\nBrazil | 21% | 83%\nIndia | 6% | 52%\nNigeria | 4% | 45%\n\n"
            "Summarise the information by selecting and reporting the main features, and make "
            "comparisons where relevant.\n\nWrite at least 150 words."
        ),
        essay(
            "WRITING TASK 2\n\nSome people think that schools should teach practical skills such as cooking "
            "and managing money, while others believe that academic subjects are more important.\n\n"
            "Discuss both views and give your own opinion.\n\nWrite at least 250 words."
        ),
    ],
}

QUIZZES = [LISTENING, READING, WRITING]
SECTION_KEYS = {'listening': LISTENING, 'reading': READING, 'writing': WRITING}
