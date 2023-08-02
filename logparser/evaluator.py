import pandas as pd
import scipy.special
import re
def evaluate(groundtruth, parsedresult, size=0):
    """ Evaluation function to benchmark log parsing accuracy

    Arguments
    ---------
        groundtruth : str
            file path of groundtruth structured csv file
        parsedresult : str
            file path of parsed structured csv file

    Returns
    -------
        f_measure : float
        accuracy : float
    """
    df_groundtruth = pd.read_csv(groundtruth)
    df_parsedlog = pd.read_csv(parsedresult, index_col=False)

    if size != 0:
        df_groundtruth = df_groundtruth[:size]
    null_logids = df_groundtruth[~df_groundtruth['EventId'].isnull()].index
    df_groundtruth = df_groundtruth.loc[null_logids]
    df_parsedlog = df_parsedlog.loc[null_logids]

    (precision, recall, f_measure, accuracy_GA, EIDS, length) = get_accuracy(df_groundtruth['EventId'], df_parsedlog['EventId'])
    # print('Precision: %.4f, Recall: %.4f, F1_measure: %.4f, accuracy_PA: %.4f'%(precision, recall, f_measure, accuracy_GA))
    PA=get_PA(EIDS,groundtruth, parsedresult)/length

    return precision, recall, f_measure, accuracy_GA, PA


def get_PA(EIDS, ground_truth, parser):

    parsermap={}
    groundmap={}
    df_parser=pd.read_csv(parser)
    df_groundtruth=pd.read_csv(ground_truth)

    for idx, line in df_parser.iterrows():
        eid=line['EventId']
        template=line['EventTemplate']
        parsermap[eid]=template
    for idx, line in df_groundtruth.iterrows():
        eid = line['EventId']
        template = line['EventTemplate']
        groundmap[eid] = template

    truth_count=0
    turthtemplate=[]
    errortemplate=[]
    for (parserEid,groundEid,count) in EIDS:
        template_parser=parsermap[parserEid]
        template_ground_truth=groundmap[groundEid]
        # print(template_parser)
        while ("(<*>)" in template_parser):
            template_parser = re.sub("\(<\*>\)", "<*>", template_parser)
        while ("(<*>)" in template_ground_truth):
            template_ground_truth = re.sub("\(<\*>\)", "<*>", template_ground_truth)
        while("<*>:<*>" in template_parser):
            template_parser=re.sub("<\*>:<\*>","<*>",template_parser)
        while ("<*>:<*>" in template_ground_truth):
            template_ground_truth = re.sub("<\*>:<\*>", "<*>", template_ground_truth)
        while("<*> <*>" in template_parser):
            template_parser=re.sub("<\*>\s<\*>","<*>",template_parser)
        while ("<*> <*>" in template_ground_truth):
            template_ground_truth = re.sub("<\*>\s<\*>", "<*>", template_ground_truth)
        while ("<*>." in template_parser):
            template_parser = re.sub("<\*>.", "<*>", template_parser)
        while ("<*>." in template_ground_truth):
            template_ground_truth = re.sub("<\*>.", "<*>", template_ground_truth)
        while("<*>##<*>" in template_parser):
            template_parser=re.sub("<\*>##<\*>","<*>",template_parser)
        while ("<*>##<*>" in template_ground_truth):
            template_ground_truth = re.sub("<\*>##<\*>", "<*>", template_ground_truth)
        while ("<*><*>" in template_parser):
            template_parser = re.sub("<\*><\*>", "<*>", template_parser)
        while ("<*><*>" in template_ground_truth):
            template_ground_truth = re.sub("<\*><\*>", "<*>", template_ground_truth)
        while ("<*>/<*>" in template_parser):
            template_parser = re.sub("<\*>/<\*>", "<*>", template_parser)
        while ("<*>/<*>" in template_ground_truth):
            template_ground_truth = re.sub("<\*>/<\*>", "<*>", template_ground_truth)
        while ("blk_<*>" in template_parser):
            template_parser = re.sub("blk_<\*>", "<*>", template_parser)
        while ("blk_<*>" in template_ground_truth):
            template_ground_truth = re.sub("blk_<\*>", "<*>", template_ground_truth)
        while ("Thunderbird_<*>" in template_parser):
            template_parser = re.sub("Thunderbird_<\*>", "<*>", template_parser)
        while ("Thunderbird_<*>" in template_ground_truth):
            template_ground_truth = re.sub("Thunderbird_<\*>", "<*>", template_ground_truth)
        while ("attempt_<*>" in template_parser):
            template_parser = re.sub("attempt_<\*>", "<*>", template_parser)
        while ("attempt_<*>" in template_ground_truth):
            template_ground_truth = re.sub("attempt_<\*>", "<*>", template_ground_truth)

        while ("/<*>" in template_parser):
            template_parser = re.sub("/<\*>", "<*>", template_parser)
        while ("/<*>" in template_ground_truth):
            template_ground_truth = re.sub("/<\*>", "<*>", template_ground_truth)

        while ("task_<*>" in template_parser):
            template_parser = re.sub("task_<\*>", "<*>", template_parser)
        while ("task_<*>" in template_ground_truth):
            template_ground_truth = re.sub("task_<\*>", "<*>", template_ground_truth)

        while ("<*>," in template_parser):
            template_parser = re.sub("<\*>,", "<*>", template_parser)
        while ("<*>," in template_ground_truth):
            template_ground_truth = re.sub("<\*>,", "<*>", template_ground_truth)

        while ("<*>;" in template_parser):
            template_parser = re.sub("<\*>;", "<*>", template_parser)
        while ("<*>;" in template_ground_truth):
            template_ground_truth = re.sub("<\*>;", "<*>", template_ground_truth)

        while ("'<*>'" in template_parser):
            template_parser = re.sub("'<\*>'", "<*>", template_parser)
        while ("'<*>'" in template_ground_truth):
            template_ground_truth = re.sub("'<\*>'", "<*>", template_ground_truth)
        while ("  " in template_parser):
            template_parser = re.sub("\s\s", " ", template_parser)
        while ("  " in template_ground_truth):
            template_ground_truth = re.sub("\s\s", " ", template_ground_truth)

        if(template_parser==template_ground_truth):
            truth_count += count
            turthtemplate.append([template_parser, template_ground_truth])
        else:
            errortemplate.append([template_parser, template_ground_truth,count])

    return truth_count


def get_accuracy(series_groundtruth, series_parsedlog, debug=False):
    """ Compute accuracy metrics between log parsing results and ground truth

    Arguments
    ---------
        series_groundtruth : pandas.Series
            A sequence of groundtruth event Ids
        series_parsedlog : pandas.Series
            A sequence of parsed event Ids
        debug : bool, default False
            print error log messages when set to True

    Returns
    -------
        precision : float
        recall : float
        f_measure : float
        accuracy : float
    """

    EIDS=[]

    series_groundtruth_valuecounts = series_groundtruth.value_counts()
    real_pairs = 0
    for count in series_groundtruth_valuecounts:
        if count > 1:
            real_pairs += scipy.special.comb(count, 2)

    series_parsedlog_valuecounts = series_parsedlog.value_counts()
    parsed_pairs = 0
    for count in series_parsedlog_valuecounts:
        if count > 1:
            parsed_pairs += scipy.special.comb(count, 2)

    accurate_pairs = 0
    accurate_events = 0 # determine how many lines are correctly parsed

    for parsed_eventId in series_parsedlog_valuecounts.index:
        logIds = series_parsedlog[series_parsedlog == parsed_eventId].index
        series_groundtruth_logId_valuecounts = series_groundtruth[logIds].value_counts()
        error_eventIds = (parsed_eventId, series_groundtruth_logId_valuecounts.index.tolist())
        error = True
        if series_groundtruth_logId_valuecounts.size == 1:
            groundtruth_eventId = series_groundtruth_logId_valuecounts.index[0]
            if logIds.size == series_groundtruth[series_groundtruth == groundtruth_eventId].size:
                accurate_events += logIds.size
                EIDS.append([parsed_eventId,groundtruth_eventId,len(logIds)])
                error = False
        if error and debug:
            print('(parsed_eventId, groundtruth_eventId) =', error_eventIds, 'failed', logIds.size, 'messages')
        for count in series_groundtruth_logId_valuecounts:
            if count > 1:
                accurate_pairs += scipy.special.comb(count, 2)

    precision = float(accurate_pairs) / parsed_pairs
    recall = float(accurate_pairs) / real_pairs
    f_measure = 2 * precision * recall / (precision + recall)
    accuracy = float(accurate_events) / series_groundtruth.size


    return precision, recall, f_measure, accuracy, EIDS, len(series_parsedlog)






