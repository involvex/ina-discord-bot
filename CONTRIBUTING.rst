Contributions
=============
Contributions to this open-source project are welcome and always appreciated! Every line of code helps
us ensure a better developed project to users. We will always credit those who help out.

New to contributing
-------------------
If you're new to contributing towards this project, we highly recommend starting off with installing
the library off of pip:

.. code-block:: bash

    pip install -U discord-py-interactions[dev]

Once you have the library installed in Python, you are able to instantiate and run a basic bot
with a logging level that is set for debugging purposes. This is recommend in order to make it easier
for us to log certain events and procedures internally that may happen before, during or after an
error may be produced:

.. code-block:: python

    import interactions
    from logging import DEBUG

    bot = interactions.Client(token="...", log_level=DEBUG) # you can also use -1.

    bot.start()

Since we are an open-source project that unofficially supports the Discord API, we also respect
the `Code of Conduct`_ from their documentation.

Where to start
--------------
Our contributions start with an **Issue**. The issue should explain what the problem you're having is.
Issues are our way and methodology of tracking bugs that may be occuring with this library. In order
to create create in relevance to the issue, you start a **Pull Request**. Linking the issue in this
(known as a PR) allows us to easily identify what bugs have been correlated with the code requesting
to be changed in the source, and allow other developers to contribute where needed.

When a PR is made, you **must** be targeting the ``unstable`` branch. This is our development branch
that we use whenever we're working on any bugfixing, breaking changes and/or overall new features. Our
development workflow for changes is from this branch to ``stable``, and then from there to a release.

Pull Request specifications
***************************
A pull request should adhere to these following requirements:

- Each git commit made on your forked project should use `conventional commits`_.
- The pull request should always be up-to-date with ``unstable``.

Recognizing contributors
------------------------
When a PR is successfully merged into one of the development branches, the GitHub user will automatically
be added to the contributor list of the repository. Additionally, we also provide a role in our support
server for contributors. (You will be notified if you are eligible for this.) The git commit history on a
file will also subsequently be updated by GitHub to include your user signature.

.. _Code of Conduct: https://github.com/discord/discord-api-docs/blob/master/CODE_OF_CONDUCT.md
.. _conventional commits: https://www.conventionalcommits.org/en/v1.0.0/
