package eu.modernmt.facade;

import eu.modernmt.aligner.Aligner;
import eu.modernmt.aligner.AlignerException;
import eu.modernmt.cluster.ClusterNode;
import eu.modernmt.engine.Engine;
import eu.modernmt.lang.LanguagePair;
import eu.modernmt.lang.UnsupportedLanguageException;
import eu.modernmt.model.Alignment;
import eu.modernmt.model.Sentence;
import eu.modernmt.model.Translation;
import eu.modernmt.processing.Preprocessor;
import eu.modernmt.processing.ProcessingException;
import eu.modernmt.processing.xml.XMLTagProjector;

/**
 * Created by davide on 20/04/16.
 */
public class TagFacade {

    private static final XMLTagProjector tagProjector = new XMLTagProjector();

    public Translation project(LanguagePair direction, String sentence, String translation) throws AlignerException, ProcessingException {
        return project(direction, sentence, translation, null);
    }

    public Translation project(LanguagePair _direction, String sentenceString, String translationString,
                               Aligner.SymmetrizationStrategy strategy) throws AlignerException, ProcessingException {
        ClusterNode node = ModernMT.getNode();
        Engine engine = node.getEngine();
        Aligner aligner = engine.getAligner();
        Preprocessor preprocessor = engine.getPreprocessor();

        LanguagePair direction = engine.getLanguageIndex().mapIgnoringDirection(_direction);

        if (direction == null)
            throw new UnsupportedLanguageException(_direction);

        Sentence sentence = preprocessor.process(direction, sentenceString);
        Sentence translation = preprocessor.process(direction.reversed(), translationString);

        Alignment alignment;

        if (strategy != null)
            alignment = aligner.getAlignment(direction, sentence, translation, strategy);
        else
            alignment = aligner.getAlignment(direction, sentence, translation);

        return tagProjector.project(new Translation(translation.getWords(), sentence, alignment));
    }

}
