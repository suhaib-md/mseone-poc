# mseONE PoC API (Local)

## Auth (local)
Use header:
Authorization: Bearer devtoken123

## Sample Queries

### Single Project

query {
  project(id: 1) { id name status }
}

### List Projects (filter + pagination)

query($first:Int!, $name:String, $after:String){
  projects(first:$first, nameContains:$name, after:$after){
    totalCount
    edges { cursor node { id name status } }
    pageInfo { hasNextPage endCursor }
  }
}

Variables:

{ "first": 2, "name": "o" }
