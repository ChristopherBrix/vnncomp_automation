from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    SubmitField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    BooleanField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from wtforms import widgets

from vnncomp.utils.aws_instance import AwsInstanceType


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class ToolkitSubmissionForm(FlaskForm):
    # https://stackoverflow.com/questions/22084886/add-a-css-class-to-a-field-in-wtform


    aws_instance_type = SelectField(
        "AWS instance type",
        choices=[
            (AwsInstanceType.T2MICRO.value, AwsInstanceType.T2MICRO.get_aws_name()),
            (AwsInstanceType.T2LARGE.value, AwsInstanceType.T2LARGE.get_aws_name()),
            (AwsInstanceType.P32XLARGE.value, AwsInstanceType.P32XLARGE.get_aws_name()),
            (
                AwsInstanceType.M516XLARGE.value,
                AwsInstanceType.M516XLARGE.get_aws_name(),
            ),
            (AwsInstanceType.G58XLARGE.value, AwsInstanceType.G58XLARGE.get_aws_name()),
        ],
    )
    repository = StringField("Git clone URL (format: https://github.com/ABC/DEF)", validators=[DataRequired()])
    hash = StringField("Commit hash", validators=[DataRequired()])
    yaml_config_file = StringField("Yaml Config File, relative to repository root", validators=[DataRequired()], render_kw={})

    post_install_tool = TextAreaField(
        "Post installation script (e.g. for licenses). Can be updated after submission (e.g. to adapt the license to the specific AWS instance)."
    )
    benchmarks = MultiCheckboxField(
        "Benchmarks",
        choices=[
            ("2022_acasxu", "2022_acasxu"),
            ("2022_cifar2020", "2022_cifar2020"),
            ("2022_carvana_unet_2022", "2022_carvana_unet_2022"),
            ("2022_cifar100_tinyimagenet_resnet", "2022_cifar100_tinyimagenet_resnet"),
            ("2022_cifar_biasfield", "2022_cifar_biasfield"),
            ("2022_collins_rul_cnn", "2022_collins_rul_cnn"),
            ("2022_mnist_fc", "2022_mnist_fc"),
            ("2022_nn4sys", "2022_nn4sys"),
            ("2022_oval21", "2022_oval21"),
            ("2022_reach_prob_density", "2022_reach_prob_density"),
            ("2022_rl_benchmarks", "2022_rl_benchmarks"),
            ("2022_sri_resnet_a", "2022_sri_resnet_a"),
            ("2022_sri_resnet_b", "2022_sri_resnet_b"),
            ("2022_tllverifybench", "2022_tllverifybench"),
            ("2022_vggnet16_2022", "2022_vggnet16_2022"),
            ("2023_cctsdb_yolo", "2023_cctsdb_yolo"),
            ("2023_cgan", "2023_cgan"),
            ("2023_collins_yolo_robustness", "2023_collins_yolo_robustness"),
            ("2023_metaroom", "2023_metaroom"),
            ("2023_ml4acopf", "2023_ml4acopf"),
            ("2023_nn4sys", "2023_nn4sys"),
            ("2023_traffic_signs_recognition", "2023_traffic_signs_recognition"),
            ("2023_vggnet16", "2023_vggnet16"),
            ("2023_vit", "2023_vit"),
            ("2023_yolo", "2023_yolo"),
        ],
        validators=[Length(min=1)],
        render_kw={"style": "list-style: none; background: #f8f9fa; border: 0px"},
    )
    run_networks = SelectField(
        "Run all instances, only one per network file or only the first one per submission",
        choices=[
            ("all", "all (final evaluation)"),
            ("different", "one per network file (for testing)"),
            ("first", "first per instance (for testing)"),
        ],
    )
    submit = SubmitField(
        "Start Evaluation", render_kw={"style": "background: #212529; color: white"}
    )


class ToolkitEditPostInstallForm(FlaskForm):
    post_install_tool = TextAreaField(
        "Post installation script (e.g. for licenses). Can be updated after submission (e.g. to adapt the license to the specific AWS instance)."
    )
    submit = SubmitField("Update script")


class BenchmarkSubmissionForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    repository = StringField("Git clone URL", validators=[DataRequired()])
    hash = StringField("Commit hash", validators=[DataRequired()])
    submit = SubmitField("Start Test", render_kw={"style": "background: #212529; color: white"})


class SignupForm(FlaskForm):
    """User Sign-up Form."""

    username = StringField(
        "Email",
        validators=[
            Length(min=6),
            Email(message="Enter a valid email."),
            DataRequired(),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=6, message="Select a stronger password."),
        ],
    )
    confirm = PasswordField(
        "Confirm Your Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    """User Log-in Form."""

    username = StringField(
        "Email", validators=[DataRequired(), Email(message="Enter a valid email.")]
    )
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")
