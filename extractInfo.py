import re
import json

# Function to remove HTML tags
def removeHtmlTags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

# Function to remove unwanted characters and text
def cleanText(text):
    text = removeHtmlTags(text)
    # text = re.sub(r'\n\s\d+.\s', '', text)  # Remove \n
    text = re.sub(r'\n*\s+\d+\.\s', '', text)  # Remove numbers at the beginning of the text
    text = re.sub(r'\s*\n+', '', text)  # Remove spaces before and after \n characters
    text = re.sub(r'\*+\s*', '', text)  # Remove ** for bold
    text = re.sub(r'\[([^\]]+)\]\(.*?\)', r'\1', text)  # Keep text within square brackets, remove hyperlinks
    text = text.replace('\n', '')  # Remove \n
    text = text.replace('&amp;', '&')  # Replace &amp; with &
    return text

def multipleElements(list):
    newList = list
    newList.insert(1, str(len(newList) - 1) + '') if len(newList) > 1 else newList
    return newList

# Function to add space between camel case
def addSpace(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    return text

# Function to get Query
def getQuery(text):
    text = text.replace('\n', '')
    return text

# Function to get Time Period
def getTimePeriod(text):

    # Define patterns for ISO 8601 durations
    patterns = {
        r'P(\d+)D': r'\1 day',  # Days
        r'PT(\d+)H': r'\1 hour',  # Hours
        r'PT(\d+)M': r'\1 minute'  # Minutes
    }

    # Apply patterns to the text
    for pattern, replacement in patterns.items():
        text = re.sub(pattern, replacement, text)
    
    
    # Conversion
    text = re.sub(r'(\d+)\s(hour)', lambda m: f"{int(m.group(1)) // 24} day" if int(m.group(1)) % 24 == 0 else m.group(0), text)
    text = re.sub(r'(\d+)\s(minute)', lambda m: f"{int(m.group(1)) // 60} hour" if int(m.group(1)) % 60 == 0 else m.group(0), text)
    
    
    # Handle pluralization
    text = re.sub(r'(\d+)\s(day|hour|minute)', lambda m: f"{m.group(1)} {m.group(2)}s" if int(m.group(1)) > 1 else m.group(0), text)
    return text

# Function to get Threshold    
def getThreshold(threshold, operator):
    patterns = {
        'GreaterThan': 'more than',
        'FewerThan': 'less than',
        'Equal': 'exactly'
    }
    return patterns[operator] + ' ' + str(threshold)

# Function to extract content types and their count
def extractContentType(text):
    contents = {}
    correspondingName = {
    "DataConnector" : "Data connector",
    "Parser" : "Parser",
    "Workbook" : "Workbook",
    "AnalyticsRule" : "Analytics rule",
    "HuntingQuery" : "Hunting query",
    "LogicAppsCustomConnector" : "Custom Azure Logic Apps Connectors",
    "Playbook" : "Playbook",
    "Watchlist" : "Watchlist"
    }
    for content in text:
        kind = content['kind']
        if kind in correspondingName:
            if correspondingName[kind] in contents:
                contents[correspondingName[kind]] += 1
            else:
                contents[correspondingName[kind]] = 1
    return contents

# Function to add Content Page Description
def addContentPageDescription():
    data = {}

    with open ('createUiDefinition.json', 'r', encoding='utf-8') as file:
        createUiDefinitionFile = file.read()
    file.close()
    
    parserCreateUiDefinitionFile = json.loads(createUiDefinitionFile)
    data.update({"contentPageDescription": cleanText(parserCreateUiDefinitionFile['parameters']['config']['basics']['description'])})

    return data

# Function to add Metadata to the parameters
def addMetadata(properties):
    data = {}

    # Basic Metadata
    data.update({"searchName": properties['displayName']})
    data.update({"solutionName": properties['source']['name']})
    data.update({"displayName": properties['displayName']})
    data.update({"contentSource": properties['source']['kind']})
    data.update({"sourceName": properties['source']['name']})
    data.update({"provider": ', '.join(properties['providers'])})
    data.update({"author": properties['author']['name']})
    data.update({"bladeSupportName": 'Microsoft' if properties['support']['name'] == "Microsoft Corporation" else properties['support']['name']})
    data.update({"supportName": properties['support']['name']})
    data.update({"category": ', '.join(sorted(properties['categories']['domains']))})
    data.update({"version": properties['version']})
    data.update({"bladeDescription": cleanText(properties['descriptionHtml'])})
    
    # Add Content Page Description
    # data.update(addContentPageDescription())

    # parameters.update({"contentCount": ', '.join([f"{contentType}: {count}" for contentType, count in sorted(extractContentType(solution['dependencies']['criteria']).items(), key = lambda item: getCustomSortingIndex(item[0]))])})
    
    # Content Type and their Count
    data.update({"contentType" : ''.join([f"{count}{contentType}" for contentType, count in sorted(extractContentType(properties['dependencies']['criteria']).items()) if contentType != "Custom Azure Logic Apps Connectors"])})

    # Total Content Count
    data.update({"contentCount":  sum(count for contentType, count in extractContentType(properties['dependencies']['criteria']).items() if contentType != "Custom Azure Logic Apps Connectors" and contentType != "Watchlist")})

    # Icons
    data.update({"solutionIcon": properties['icon']})
    data.update({'versionIcon' : "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTAgMi42NTYyNUgxMS45ODc1VjkuNjA1NzRDMTEuOTg3NSA5LjcxNjI4IDExLjk0NTMgOS44MjIyOSAxMS44NzAxIDkuOTAwNDRDMTEuNzk1IDkuOTc4NiAxMS42OTMgMTAuMDIyNSAxMS41ODY4IDEwLjAyMjVIMC40MDA3NUMwLjI5NDQ2NCAxMC4wMjI1IDAuMTkyNTMyIDkuOTc4NiAwLjExNzM3NyA5LjkwMDQ0QzAuMDQyMjIxOCA5LjgyMjI5IDAgOS43MTYyOCAwIDkuNjA1NzRWMi42NTYyNVoiIGZpbGw9InVybCgjcGFpbnQwX2xpbmVhcikiLz4KPHBhdGggZD0iTTAuNDAyNSAzLjk3NDAzZS0wNkgxMS41ODI0QzExLjY4ODcgMy45NzQwM2UtMDYgMTEuNzkwNiAwLjA0MzkxMzUgMTEuODY1NyAwLjEyMjA3M0MxMS45NDA5IDAuMjAwMjMyIDExLjk4MzEgMC4zMDYyMzkgMTEuOTgzMSAwLjQxNjc3NFYyLjY1NjIzSDBWMC40MTY3NzRDLTUuMDMxNjdlLTA3IDAuMzYxODg5IDAuMDEwNDIyOSAwLjMwNzU0NSAwLjAzMDY3MTggMC4yNTY4NjFDMC4wNTA5MjA3IDAuMjA2MTc3IDAuMDgwNTk2NCAwLjE2MDE1MiAwLjExNzk5NSAwLjEyMTQyOEMwLjE1NTM5NCAwLjA4MjcwMzEgMC4xOTk3NzkgMC4wNTIwNDIyIDAuMjQ4NjAyIDAuMDMxMjA0OUMwLjI5NzQyNiAwLjAxMDM2NzYgMC4zNDk3MjYgLTAuMDAwMjM1Njk2IDAuNDAyNSAzLjk3NDAzZS0wNloiIGZpbGw9IiMwMDc4RDQiLz4KPHBhdGggZD0iTTIuMDEyNyA2LjYzMzc5SDE0LjAwMDJWMTMuNTgzM0MxNC4wMDAyIDEzLjY5MzggMTMuOTU4IDEzLjc5OTggMTMuODgyOCAxMy44NzhDMTMuODA3NyAxMy45NTYxIDEzLjcwNTcgMTQuMDAwMSAxMy41OTk0IDE0LjAwMDFIMi40MTUyQzIuMzA4OTEgMTQuMDAwMSAyLjIwNjk4IDEzLjk1NjEgMi4xMzE4MiAxMy44NzhDMi4wNTY2NyAxMy43OTk4IDIuMDE0NDUgMTMuNjkzOCAyLjAxNDQ1IDEzLjU4MzNWNi42MzM3OUgyLjAxMjdaIiBmaWxsPSJ1cmwoI3BhaW50MV9saW5lYXIpIi8+CjxwYXRoIGQ9Ik0yLjQxNzgyIDMuOTczNjZIMTMuNTk3N0MxMy42NTA0IDMuOTczNDIgMTMuNzAyNiAzLjk4Mzk5IDEzLjc1MTQgNC4wMDQ3N0MxMy44MDAyIDQuMDI1NTUgMTMuODQ0NSA0LjA1NjEzIDEzLjg4MTkgNC4wOTQ3NkMxMy45MTkzIDQuMTMzMzkgMTMuOTQ5IDQuMTc5MzEgMTMuOTY5MyA0LjIyOTg4QzEzLjk4OTYgNC4yODA0NiAxNC4wMDAxIDQuMzM0NzEgMTQuMDAwMiA0LjM4OTUyVjYuNjMzNTJIMi4wMTI3VjQuMzg5NTJDMi4wMTI4MSA0LjMzNDQ4IDIuMDIzNCA0LjI4MDAxIDIuMDQzODcgNC4yMjkyNUMyLjA2NDMzIDQuMTc4NDkgMi4wOTQyNiA0LjEzMjQ1IDIuMTMxOTMgNC4wOTM3OUMyLjE2OTU5IDQuMDU1MTIgMi4yMTQyNSA0LjAyNDYgMi4yNjMzMiA0LjAwMzk4QzIuMzEyMzkgMy45ODMzNiAyLjM2NDkgMy45NzMwNiAyLjQxNzgyIDMuOTczNjZaIiBmaWxsPSIjMTk4QUIzIi8+CjxkZWZzPgo8bGluZWFyR3JhZGllbnQgaWQ9InBhaW50MF9saW5lYXIiIHgxPSI1Ljk5Mjg4IiB5MT0iMTAuMDIxNiIgeDI9IjUuOTkyODgiIHkyPSIyLjY1NjI1IiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CjxzdG9wIHN0b3AtY29sb3I9IiMwMDc4RDQiLz4KPHN0b3Agb2Zmc2V0PSIwLjUwMiIgc3RvcC1jb2xvcj0iIzQwOTNFNiIvPgo8c3RvcCBvZmZzZXQ9IjAuNzc1IiBzdG9wLWNvbG9yPSIjNUVBMEVGIi8+CjwvbGluZWFyR3JhZGllbnQ+CjxsaW5lYXJHcmFkaWVudCBpZD0icGFpbnQxX2xpbmVhciIgeDE9IjguMDA3MzIiIHkxPSIxMy45OTU1IiB4Mj0iOC4wMDczMiIgeTI9IjYuNjI5MjQiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KPHN0b3Agc3RvcC1jb2xvcj0iIzMyQkVERCIvPgo8c3RvcCBvZmZzZXQ9IjAuMTc1IiBzdG9wLWNvbG9yPSIjMzJDQUVBIi8+CjxzdG9wIG9mZnNldD0iMC40MSIgc3RvcC1jb2xvcj0iIzMyRDJGMiIvPgo8c3RvcCBvZmZzZXQ9IjAuNzc1IiBzdG9wLWNvbG9yPSIjMzJENEY1Ii8+CjwvbGluZWFyR3JhZGllbnQ+CjwvZGVmcz4KPC9zdmc+Cg=="})

    return data

# Function to sort in order
def getCustomSortingIndex(contentType):
    contentSortingOrder = ["Data Connectors", "Parsers", "Workbooks", "Analytic Rules", "Hunting Queries", "Custom Azure Logic Apps Connectors", "Playbooks"]

    if contentType in contentSortingOrder:
        return contentSortingOrder.index(contentType)
    return len(contentSortingOrder)

# Function to add Data Connectors to the parameters
def addDataConnectors(content, dataConnector, dataConnectorMapping):
    resource = content['mainTemplate']['resources'][0]
    dataConnector.append({
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "dataConectorId": content['contentId'],
        "dataTypes" : ''.join([dataType['name'] + ' --' for dataType in resource['properties']['connectorUiConfig']['dataTypes']]),
        "description": cleanText(resource['properties']['connectorUiConfig']['descriptionMarkdown']),
        "provider": resource['properties']['connectorUiConfig']['publisher'],
        "version": content['version']
    })

    dataConnectorMapping.update({content['contentId'].lower() : content['displayName']})

# Function to add Workbooks to the parameters
def addWorkbooks(content, workbook):
    resources = content['mainTemplate']['resources']
    workbook.append({
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(resources[0]['metadata']['description']),
        "version": content['version'],
        "dataTypes": ''.join([dataType['contentId'] + ' --' for dataType in resources[-1]['properties']['dependencies']['criteria'] if dataType["kind"] == "DataType"] if 'dependencies' in resources[-1]['properties'] else '',),
        "dataConnectorId": ' '.join([dataConnector['contentId'] for dataConnector in resources[-1]['properties']['dependencies']['criteria'] if dataConnector["kind"] == "DataConnector"] if 'dependencies' in resources[-1]['properties'] else []),
    })

# Function to add Analytics Rules to the parameters
def addAnalyticsRule(content, analyticsRule, dataConnectorMapping):
    resource = content['mainTemplate']['resources'][0]

    dataConnectorId = []
    dataConnectorName = []
    dataTypes = set()
        
    for dataConnector in resource['properties']['requiredDataConnectors']:
        dataConnectorId.append(dataConnector['connectorId'])
        dataConnectorName.append(dataConnectorMapping[dataConnector['connectorId'].lower()])
        for dataType in dataConnector['dataTypes']:
            dataTypes.add(dataType + ' --')



    analyticsRule.append({
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(resource['properties']['description']),
        "version": content['version'],
        "ruleType" : resource['kind'],
        "severity": resource['properties']['severity'],
        
        "query": getQuery(resource['properties']['query']),

        "ruleFrequency": getTimePeriod(resource['properties']['queryFrequency']) if 'queryFrequency' in resource['properties'] else '' ,
        "rulePeriod": getTimePeriod(resource['properties']['queryPeriod']) if 'queryPeriod' in resource['properties'] else '',
        "suppressionDuration": getTimePeriod(resource['properties']['suppressionDuration']) if 'suppressionDuration' in resource['properties'] else '',
        'thresholdTrigger': getThreshold(resource['properties']['triggerThreshold'], resource['properties']['triggerOperator']) if 'triggerThreshold' in resource['properties'] else '',

        "mitreAttack": [addSpace(technique) for technique in resource['properties']['tactics']] if 'tactics' in resource['properties'] else [],
        "mitreAttackMultiple": ''.join(multipleElements([addSpace(technique) for technique in resource['properties']['tactics']])) if 'tactics' in resource['properties'] else [],
        "techniques": resource['properties']['techniques'] if 'techniques' in resource['properties'] else [],
        "techniquesMultiple": ''.join(multipleElements([element for element in resource['properties']['techniques']])) if 'techniques' in resource['properties'] else [],
        "subTechniques": resource['properties']['subTechniques'] if 'subTechniques' in resource['properties'] else [],
        "subTechniquesMultiple": ''.join(multipleElements([element for element in resource['properties']['subTechniques']])) if 'subTechniques' in resource['properties'] else [],
        "entityMapping": resource['properties']['entityMappings'] if 'entityMappings' in resource['properties'] else [],

        "dataConnectorId" : dataConnectorId[0],
        "dataConnectorName" : dataConnectorName[0],
        "dataTypes" : ''.join(dataTypes),
    })

# Function to add Hunting Queries to the parameters
def addHuntingQueries(content, huntingQueries):
    resource = content['mainTemplate']['resources'][0]
    
    mitreAttack = []
    techniques = []
    for tag in resource['properties']['tags']:
        if tag['name'] == 'tactics':
            mitreAttack.append(addSpace(tag['value']))
        elif tag['name'] == 'techniques':
            techniques.append(tag['value'])

    huntingQueries.append({
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(resource['properties']['tags'][0]['value'] if resource['properties']['tags'][0]['name'] == 'description' else ''),
        "version": content['version'],

        "query": getQuery(resource['properties']['query']),

        "mitreAttack": mitreAttack,
        "techniques": techniques,
    })

# Function to add Parsers to the parameters
def addParsers(content, parser):
    parser.append({
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "functionAlias" : content['mainTemplate']['resources'][0]['properties']['functionAlias'],
        "version": content['version'],
        "query": getQuery(content['mainTemplate']['resources'][0]['properties']['query']),
    })

# Function to add Logic Apps Custom Connectors to the parameters
def addLogicAppsCustomConnectors(content, logicAppsCustomConnector):
    logicAppsCustomConnector.append({
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(content['mainTemplate']['resources'][0]['properties']['description']),
        "version": content['version'],

    })

# Function to add Playbooks to the parameters
def addPlaybook(content, playbook):
    metadata = content['mainTemplate']['metadata']

    if 'entities' in metadata:
        metadata['entities'] = multipleElements(metadata['entities'])

    playbook.append({
        "displayName": content['displayName'],
        "description": cleanText(metadata['description']),
        "version": content['version'],
        "prerequisites": ''.join([cleanText(prerequisite) for prerequisite in metadata['prerequisites']]),
        "postDeployment" : ''.join(cleanText(postDeployment) for postDeployment in metadata['postDeployment']) if 'postDeployment' in metadata else '',
        "entities": metadata['entities'] if 'entities' in metadata else [],
        "entitiesMultiple": ''.join(metadata['entities']) if 'entities' in metadata else '',
        "tags": ''.join(metadata['tags']) if 'tags' in metadata else '',        

    })

# Function to add Watchlist to the parameters
def addWatchlist(content, watchlist):
    watchlist.append({
        "displayName": content['displayName'],
        "description": cleanText(content['description']),
        "source" : content['source'],
        "alias" : content['watchlistAlias'],
        "provider": content['provider'],
        "itemsSearchKey": content['itemsSearchKey'],
        "rawContent": content['rawContent']
    })

# Function to add Contents to the parameters
def addContents(contents):
    dataConnector = []
    workbook = []
    analyticsRule = []
    huntingQuery = []
    parser = []
    logicAppsCustomConnector = []
    playbook = []
    watchlist = []

    data = {}

    dataConnectorMapping = {}

    for content in contents:
        if 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'DataConnector':
            addDataConnectors(content['properties'], dataConnector, dataConnectorMapping)
        elif 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'Workbook':
            addWorkbooks(content['properties'], workbook)
        elif 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'AnalyticsRule':
            addAnalyticsRule(content['properties'], analyticsRule, dataConnectorMapping)
        elif 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'HuntingQuery':
            addHuntingQueries(content['properties'], huntingQuery)
        elif 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'Parser':
            addParsers(content['properties'], parser)
        elif 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'LogicAppsCustomConnector':
            addLogicAppsCustomConnectors(content['properties'], logicAppsCustomConnector)
        elif 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'Playbook':
            addPlaybook(content['properties'], playbook)
        elif 'type' in content and content['type'] == 'Microsoft.OperationalInsights/workspaces/providers/Watchlists':
            addWatchlist(content['properties'], watchlist)

    data.update({"dataConnector": dataConnector})
    data.update({"workbook": workbook})
    data.update({"analyticsRule": analyticsRule})
    data.update({"huntingQuery": huntingQuery})
    data.update({"parser": parser})
    data.update({"logicAppsCustomConnector": logicAppsCustomConnector})
    data.update({"playbook": playbook})
    data.update({"watchlist": watchlist})
    
    return data

# Sort to make dataConnector first
def sortContents(content):
        if 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'DataConnector':
            return (0, content['properties']['contentKind'])
        return (1, content['properties']['contentKind'] if 'contentKind' in content['properties'] else content['type'])

# Function to extract information from the mainTemplate.json file    
def extractInfo(resources):
    testData = {}

    contents = []

    for resource in resources:
        if resource['type'] == "Microsoft.OperationalInsights/workspaces/providers/contentPackages":
            testData.update(addMetadata(resource['properties']))
        elif 'contentKind' in resource['properties'] and (resource['properties']['contentKind'] == 'DataConnector'
        or resource['properties']['contentKind'] == 'Workbook'
        or resource['properties']['contentKind'] == 'AnalyticsRule'
        or resource['properties']['contentKind'] == 'HuntingQuery'
        or resource['properties']['contentKind'] == 'Parser'
        or resource['properties']['contentKind'] == 'LogicAppsCustomConnector'
        or resource['properties']['contentKind'] == 'Playbook') or 'type' in resource and resource['type'] == 'Microsoft.OperationalInsights/workspaces/providers/Watchlists':
            contents.append(resource)

    contents.sort(key=sortContents)

    testData.update(addContents(contents))

    return testData
                
# Main function
def main():
    # Read the content of mainTemplate.json
    with open('mainTemplate.json', 'r', encoding='utf-8') as file:
        mainTemplateFile = file.read()

    file.close()

    # Load the JSON content
    parsedMainTemplateFile = json.loads(mainTemplateFile)
    resources = parsedMainTemplateFile['resources']


    testData = extractInfo(resources)

    # solution = parsedMainTemplateFile[-1]['properties']

    variables = parsedMainTemplateFile['variables']
    parameters = parsedMainTemplateFile['parameters']

    for parameter in parameters:
        parameters[parameter] = parameters[parameter]['defaultValue']

    with open('testData.json', 'w', encoding='utf-8') as file:
        json.dump(testData, file, indent=4)

    file.close()
    print("done")

if __name__ == "__main__":
    main()
