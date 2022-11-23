from vnncomp import create_app

app = create_app()


if __name__ == "__main__":
    # import vnncomp.views, vnncomp.auth

    app.run(debug=True, host="0.0.0.0") # only for debuggin, not for production
