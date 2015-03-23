# Invoke (pyinvoke.org) tab-completion script to the fish shell
# Copy it to the ~/.config/fish/completions directory

function __complete_invoke
    invoke --complete -- (commandline --tokenize)
end

# --no-files: Don't complete files unless invoke gives an empty result
complete --command invoke --no-files --arguments '(__complete_invoke)'
