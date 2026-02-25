"""
Management command to populate HistoryArticle with sample Igala history content for testing.
Usage: python manage.py populate_history
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from history.models import HistoryArticle


SAMPLE_ARTICLES = [
    {
        "title": "The Origin of the Igala Kingdom",
        "excerpt": "The Igala people trace their roots to the ancient Jukun and Benin influences, with Idah as the traditional capital.",
        "content_english": """
        <p>The Igala Kingdom is one of the oldest traditional states in Nigeria, with a history that spans several centuries. 
        The kingdom is located in the middle belt of Nigeria, with Idah as its traditional capital on the eastern bank of the River Niger.</p>
        <p>Oral traditions suggest that the Igala people migrated from various directions—some from the Jukun area, others from Benin—and 
        eventually consolidated into a unified kingdom. The <strong>Ata Igala</strong> (king) is the paramount ruler and custodian of 
        the land and culture.</p>
        <p>Today, the Igala kingdom continues to preserve its customs, language, and identity despite the changes brought by modernity.</p>
        """,
        "content_igala": """
        <p>Oma Igala du ojo oche ewu. Idah ni odu oma. Ata Igala ni eche ewu.</p>
        <p>Ega Igala ma du ojo oche ewu ebi Nigeria. Ebi Idah ni odu oma.</p>
        """,
    },
    {
        "title": "The Ata Igala: Custodian of the Throne",
        "excerpt": "The Ata Igala is the spiritual and traditional head of the Igala kingdom, embodying the unity and heritage of the people.",
        "content_english": """
        <p>The <strong>Ata Igala</strong> is the paramount ruler of the Igala kingdom. The title "Ata" means "father" or "owner of the land," 
        and the Ata is seen as the father of all Igala people and the custodian of the land.</p>
        <p>The coronation of a new Ata involves elaborate rituals and ceremonies that connect the living with ancestors and the divine. 
        The Ata's palace in Idah remains a central symbol of Igala identity and authority.</p>
        <p>Throughout history, the Ata has played a key role in mediating disputes, upholding customs, and representing the Igala 
        people in wider Nigerian and regional affairs.</p>
        """,
        "content_igala": """
        <p>Ata Igala ni eche ewu. Ata ni odu oma Igala. Idah ni odu oma.</p>
        """,
    },
    {
        "title": "Igala Festivals and Cultural Celebrations",
        "excerpt": "From Ocho to Egwu Ota, Igala festivals mark the seasons, honour ancestors, and strengthen community bonds.",
        "content_english": """
        <p>Igala culture is rich in festivals that mark the agricultural calendar, honour ancestors, and bring communities together.</p>
        <h3>Ocho Festival</h3>
        <p>Ocho is one of the most significant festivals, often associated with the harvest and the renewal of the land. 
        It involves masquerades, dance, and rituals that reaffirm the people's connection to the earth and their ancestors.</p>
        <h3>Egwu Ota and Other Celebrations</h3>
        <p>Other celebrations include Egwu Ota and various local ceremonies that differ from one district to another. 
        Music, dance, and storytelling are central to these events, passing down history and values from one generation to the next.</p>
        """,
        "content_igala": "",
    },
    {
        "title": "Idah: The Heart of Igala Land",
        "excerpt": "Idah, on the banks of the Niger, has been the political and cultural centre of the Igala kingdom for centuries.",
        "content_english": """
        <p><strong>Idah</strong> is the traditional capital of the Igala kingdom, situated on the eastern bank of the River Niger in 
        present-day Kogi State. For centuries, it has served as the political, cultural, and spiritual centre of Igala land.</p>
        <p>The town is home to the Ata's palace, historic shrines, and landmarks that tell the story of the kingdom. 
        The Niger River has not only provided sustenance and trade routes but also shaped the identity and economy of the people.</p>
        <p>Today, Idah remains a symbol of Igala heritage and a place where tradition and modernity meet.</p>
        """,
        "content_igala": "",
    },
    {
        "title": "Igala Language and Oral Tradition",
        "excerpt": "The Igala language is a key part of the people's identity, preserved through proverbs, stories, and daily use.",
        "content_english": """
        <p>The <strong>Igala language</strong> (Igala: ága Ígáláà) is a Yoruboid language spoken by the Igala people. 
        It is closely related to Yoruba and Itsekiri and is an important marker of Igala identity.</p>
        <p>Oral tradition has been the primary means of preserving history, laws, and wisdom. Proverbs, folktales, and 
        songs carry lessons and connect the community to its past. Efforts to document and teach the language in schools 
        and through digital platforms aim to ensure it thrives for future generations.</p>
        <p>Projects like IgalaHeritage contribute to this goal by building dictionaries, recording pronunciations, and 
        sharing stories in both Igala and English.</p>
        """,
        "content_igala": """
        <p>Ága Ígáláà ni eche ewu. Ega ma du ojo oche ewu. Ebi oma Igala.</p>
        """,
    },
    {
        "title": "Igala and the River Niger",
        "excerpt": "The Niger River has shaped Igala economy, culture, and identity through fishing, trade, and spiritual beliefs.",
        "content_english": """
        <p>The <strong>River Niger</strong> flows along the western boundary of Igala land and has deeply influenced the way of life 
        of the people. Fishing, farming on the floodplains, and trade along the river have been central to the economy for generations.</p>
        <p>The river also features in Igala cosmology and folklore. Many communities regard it as sacred and link it to 
        creation stories and the blessings of the land. Seasonal floods bring fertility to the soil, supporting agriculture 
        and sustaining livelihoods.</p>
        <p>In modern times, the river continues to be a vital resource and a symbol of the natural heritage of the Igala people.</p>
        """,
        "content_igala": "",
    },
]


class Command(BaseCommand):
    help = "Populate HistoryArticle with sample Igala history articles for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing HistoryArticle objects before populating.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        contributor = User.objects.filter(is_superuser=True).first() or User.objects.first()

        if options["clear"]:
            count = HistoryArticle.objects.count()
            HistoryArticle.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing history article(s)."))

        created = 0
        for item in SAMPLE_ARTICLES:
            if HistoryArticle.objects.filter(title=item["title"]).exists():
                self.stdout.write(f"  Skipping (already exists): {item['title']}")
                continue
            HistoryArticle.objects.create(
                title=item["title"],
                excerpt=item["excerpt"].strip(),
                content_english=item["content_english"].strip(),
                content_igala=item["content_igala"].strip() or "",
                contributor=contributor,
            )
            created += 1
            self.stdout.write(f"  Created: {item['title']}")

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} history article(s). Total: {HistoryArticle.objects.count()}"))
