import click
from .commands.photo import photo
from .commands.video import video
from .commands.story_photo import story_photo
from .commands.story_video import story_video

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def post():
    pass


post.add_command(photo)
post.add_command(video)
post.add_command(story_photo)
post.add_command(story_video)
