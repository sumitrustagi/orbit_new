"""Team and channel management forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class CreateTeamForm(FlaskForm):
    display_name = StringField(
        "Team Name",
        validators=[DataRequired(), Length(min=2, max=255)],
    )
    description = TextAreaField(
        "Description",
        validators=[Optional(), Length(max=1000)],
    )
    visibility = SelectField("Visibility", choices=[
        ("private", "Private"),
        ("public",  "Public"),
    ], default="private")
    owner_id = StringField("Owner (User ID)", validators=[Optional()])
    submit   = SubmitField("Create Team")


class CreateChannelForm(FlaskForm):
    display_name = StringField(
        "Channel Name",
        validators=[DataRequired(), Length(min=2, max=255)],
    )
    description = TextAreaField(
        "Description",
        validators=[Optional(), Length(max=1000)],
    )
    membership_type = SelectField("Type", choices=[
        ("standard", "Standard"),
        ("private",  "Private"),
        ("shared",   "Shared"),
    ], default="standard")
    submit = SubmitField("Create Channel")


class CreateMeetingForm(FlaskForm):
    subject    = StringField("Subject", validators=[DataRequired(), Length(max=512)])
    start_time = StringField("Start Time (ISO 8601)", validators=[DataRequired()])
    end_time   = StringField("End Time (ISO 8601)", validators=[DataRequired()])
    user_id    = StringField("Organizer User ID", validators=[DataRequired()])
    submit     = SubmitField("Create Meeting")
