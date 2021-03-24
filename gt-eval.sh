echo "Existing results:"
./gt-list-results.sh
echo
echo "Gathering missing results"
set -x
./gt-bleu.sh cs en wmt18
./gt-bleu.sh de en wmt20
./gt-bleu.sh es en wmt13
./gt-bleu.sh et en wmt18
./gt-bleu.sh fr en wmt15
./gt-bleu.sh pl en wmt20
./gt-bleu.sh en cs wmt19
./gt-bleu.sh en de wmt20
./gt-bleu.sh en es wmt13
./gt-bleu.sh en et wmt18
./gt-bleu.sh en fr wmt15
./gt-bleu.sh en pl wmt20
set +x
echo
echo "Updated results:"
./gt-list-results.sh
echo
