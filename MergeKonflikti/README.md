# Merge conflicts on purpose - left unresolved

Five deliberate merge conflicts. Each one was produced by a real `git merge` and each one
was **left unresolved on purpose**: the merge commit was made with the conflict markers
still inside the file. Every conflict has its own file, so you can fix them one by one.

| # | File | What clashed | Suggested way to resolve |
|---|------|--------------|--------------------------|
| 1 | `1_sveiciens.txt` | both sides rewrote the same greeting line | keep **ours** |
| 2 | `2_iestatijumi.ini` | both sides set a different number on the same line | keep **theirs** |
| 3 | `3_iepirkumu_saraksts.txt` | both sides added a different line at the end of the list | keep **both** lines |
| 4 | `4_cena.py` | both sides changed the same `return` line (VAT vs. discount) | **combine** both ideas (discount first, then VAT, prints `Kopā: 10.89 EUR`) |
| 5 | `5_plans.md` | both sides rewrote the same two list items | take **one line from each** side |

*Ours* is the side that was merged into (`HEAD`); *theirs* is the commit that was merged in.
The "theirs" side of every merge is an ordinary commit (the second parent of the merge
commit); it never had a branch name.

## Reading a conflict

```
  <<<<<<< HEAD          start: OUR version
  ...our lines...
  =======               separator
  ...their lines...
  >>>>>>> <commit>      end: THEIR version (<commit> is the commit that was merged in)
```

The markers are indented here only so that this README is not itself mistaken for a
conflict. In the five files they start at the very beginning of the line.

## Find what is still unresolved

`git status` says "clean", because the merges were committed with the markers inside.
Ask `git grep` instead:

```
git grep -nE "^(<<<<<<<|=======|>>>>>>>)"
```

It lists every unresolved spot and prints nothing once everything is fixed.
`4_cena.py` will not even run (SyntaxError) until conflict 4 is resolved.

## Resolve them

1. Open a file and decide what the final text should be.
2. Delete the three marker lines and the lines you do not want to keep.
3. Save, then `git add <file>` and `git commit`.

(`git checkout --ours/--theirs` do nothing here, because git no longer sees these files as
conflicted. They only work in the "live" version below.)

## Try the "live" version (git status shows "Unmerged paths")

```
git log --merges --format="%h %p  %s"    # merge commit, our side, their side, message
git switch --detach <our side>           # the commit before the merge
git merge <their side>                   # git stops with the conflict again
```

Now `git status`, `git checkout --ours/--theirs <file>`, `git add` and `git commit` work the
way they do in a real merge. To give up instead: `git merge --abort`, then `git switch -`.

## Prove that a merge really conflicted (Git 2.38+)

```
git merge-tree --write-tree --name-only <our side> <their side>
```

It exits with status 1 and prints the name of the conflicting file.
