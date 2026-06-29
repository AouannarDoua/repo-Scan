#!/usr/bin/env python3
"""
cli.py — Interface en ligne de commande.

    python cli.py <repo> --ask "où est gérée l'authentification ?"
    python cli.py <repo> --critical
    python cli.py <repo> --tree
"""
import argparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend import RepoAssistant


def main():
    p = argparse.ArgumentParser(description="Repo Lens — assistant d'analyse de repository")
    p.add_argument("repo", help="chemin du repository à analyser")
    p.add_argument("--ask", metavar="QUESTION", help="poser une question en langage naturel")
    p.add_argument("--critical", action="store_true", help="lister les fichiers critiques")
    p.add_argument("--tree", action="store_true", help="afficher l'arborescence indexée")
    p.add_argument("-k", type=int, default=4, help="nombre d'extraits à récupérer")
    args = p.parse_args()

    assistant = RepoAssistant(args.repo).build()
    s = assistant.stats()
    print(f"[index] {s['files']} fichiers · {s['chunks']} chunks "
          f"({s['code']} code, {s['doc']} doc, {s['config']} config)\n")

    if args.critical:
        for c in assistant.critical()[:10]:
            print(f"  {c['score']:>5}  {c['path']}")
            for r in c["reasons"]:
                print(f"           - {r}")
    elif args.tree:
        for f in assistant.tree():
            print(f"  [{f['category'][:4]}] {f['path']} ({f['n_lines']} l.)")
    elif args.ask:
        res = assistant.ask(args.ask, k=args.k)
        print(f"Mode : {res['mode']} · Confiance : {res['confidence']}\n")
        print(res["answer"])
        if res["sources"]:
            print("\nSources : " +
                  ", ".join(f"{x['file']}:{x['start']}-{x['end']}" for x in res["sources"]))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
