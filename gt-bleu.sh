SRC=$1
TRG=$2
TESTSET=$3
TESTSET_PATH_COMPONENT=${TESTSET/\//_}

INPUT_FILE=bleu-results/gt.$TESTSET_PATH_COMPONENT.$SRC$TRG.src.txt
OUTPUT_FILE=bleu-results/gt.$TESTSET_PATH_COMPONENT.$SRC$TRG.txt
COMPARISON_FILE=bleu-results/gt.$TESTSET_PATH_COMPONENT.$SRC$TRG.ref.txt
BLEU_FILE=bleu-results/gt.$TESTSET_PATH_COMPONENT.$SRC$TRG.bleu.txt

set -e
set -o pipefail
#set -x

mkdir -p bleu-results

if [ ! -s $INPUT_FILE ]; then
  sacrebleu -t $TESTSET -l $SRC-$TRG --echo src > $INPUT_FILE
fi
if [ ! -s $COMPARISON_FILE ]; then
  sacrebleu -t $TESTSET -l $SRC-$TRG --echo ref > $COMPARISON_FILE
fi
if [ ! -s $INPUT_FILE ]; then
  exit 1
fi

wc $INPUT_FILE

if [ ! -s $OUTPUT_FILE ]; then
  echo "### Translating $TESTSET $SRC-$TRG using Google Translate"
  if python gt.py -s $SRC -t $TRG --input $INPUT_FILE --output $OUTPUT_FILE.tmp; then
    mv $OUTPUT_FILE.tmp $OUTPUT_FILE
  fi
fi

wc $OUTPUT_FILE
wc $COMPARISON_FILE

if [ -s $OUTPUT_FILE ]; then
  if [ ! -s $BLEU_FILE ]; then
    sacrebleu -t $TESTSET -l $SRC-$TRG < $OUTPUT_FILE | tee $BLEU_FILE
  fi
fi
